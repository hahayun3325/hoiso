from pathlib import Path
import json
import os
os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")
import numpy as np
import trimesh
from PIL import Image
from scipy.spatial import cKDTree
from scipy.ndimage import binary_erosion

DATA = Path("/home/fredcui/foho_phase0")
TOKEN = "alapuse02v3c"
RUN_ROOT = DATA / "phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse02_v3c_selector_v41_refined_pipeline"
CASE_ROOT = DATA / "phase2_gateA_part_recon/cases/alapuse02_v3c"
V02 = CASE_ROOT / "integrated_gates/gate_c_v0_2_object_only_masked_realign"
for d in ["outputs", "visuals", "metrics", "decisions"]:
    (V02 / d).mkdir(parents=True, exist_ok=True)

DECISION_JSON = V02 / "metrics" / "v0_2_realign_decision.json"
if DECISION_JSON.exists():
    raise SystemExit(f"[ABORT] {DECISION_JSON} exists — no-clobber")

# ---------- 1. object-only MoGe target ----------
def load_points_exr(p):
    import cv2
    arr = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    if arr is None:
        raise SystemExit(f"[FAIL] cannot read {p} (need opencv with EXR; else pip install imageio[freeimage])")
    return arr[..., :3].astype(np.float64)

points_exr = RUN_ROOT / f"moge_out/{TOKEN}_cropped_hoi/points.exr"
points_npy = points_exr.with_suffix(".npy")
if points_npy.exists():
    print(f"[target] loading cached npy points: {points_npy}")
    pts_img = np.load(points_npy).astype(np.float64)
else:
    pts_img = load_points_exr(points_exr)               # H x W x 3
H, W = pts_img.shape[:2]

mask_candidates = sorted(RUN_ROOT.rglob(f"*{TOKEN}*obj*mask*.png"))
if not mask_candidates:
    raise SystemExit("[FAIL] no object mask found — set path manually")
mask_path = mask_candidates[0]
mask = np.array(Image.open(mask_path).convert("L").resize((W, H), Image.NEAREST)) > 127
mask = binary_erosion(mask, iterations=4)           # kill boundary/hand-edge bleed

tgt = pts_img[mask]
tgt = tgt[np.isfinite(tgt).all(axis=1)]
tgt = tgt[np.abs(tgt).sum(axis=1) > 1e-8]
c = tgt.mean(0); d = np.linalg.norm(tgt - c, axis=1)
tgt = tgt[d < np.percentile(d, 98)]                 # SOR-lite
if len(tgt) < 2000:
    raise SystemExit(f"[FAIL] only {len(tgt)} target points after masking — check mask/exr alignment")
print(f"[target] {len(tgt)} object-only MoGe points (mask: {mask_path.name})")

# ---------- 2. source mesh + old T ----------
src_mesh = trimesh.load(CASE_ROOT / "gate_a_early/object_only_hunyuan_decode_v4_corrected" / f"{TOKEN}_hoi_mesh.ply", process=False)
if isinstance(src_mesh, trimesh.Scene):
    src_mesh = trimesh.util.concatenate([g for g in src_mesh.geometry.values() if hasattr(g, "vertices")])
src0, _ = trimesh.sample.sample_surface(src_mesh, 8000)
src0 = np.asarray(src0, dtype=np.float64)

T_old = np.load(CASE_ROOT / "gate_c_experiment/h2m_object_only_out" / f"{TOKEN}_object_only_hoi_mesh.npy")
s_old = np.linalg.svd(T_old[:3, :3], compute_uv=False)[0]

# ---------- 3. trimmed-ICP with Umeyama similarity ----------
def umeyama(A, B):     # fit s,R,t mapping A -> B
    muA, muB = A.mean(0), B.mean(0)
    Ac, Bc = A - muA, B - muB
    cov = Bc.T @ Ac / len(A)
    U, S, Vt = np.linalg.svd(cov)
    D = np.diag([1.0, 1.0, np.sign(np.linalg.det(U @ Vt))])
    R = U @ D @ Vt
    s = np.trace(np.diag(S) @ D) / (Ac ** 2).sum() * len(A)
    t = muB - s * R @ muA
    T = np.eye(4); T[:3, :3] = s * R; T[:3, 3] = t
    return T, float(s)

def apply_T(P, T):
    return P @ T[:3, :3].T + T[:3, 3]

tree = cKDTree(tgt)
T_cur = T_old.copy()
for it in range(20):
    cur = apply_T(src0, T_cur)
    dist, idx = tree.query(cur)
    keep = dist < np.percentile(dist, 80)           # trim worst 20%
    T_cur, s_cur = umeyama(src0[keep], tgt[idx[keep]])
    if it % 5 == 0 or it == 19:
        print(f"[icp {it:02d}] inlier_mean={dist[keep].mean():.4f} scale={s_cur:.4f} (old {s_old:.4f})")

np.save(V02 / "outputs" / f"{TOKEN}_object_only_masked_T_v0_2.npy", T_cur)

# ---------- 4. apply ONE T to BOTH parts; fingertip check ----------
part_dir = CASE_ROOT / "part_meshes_partfield_n2_vmap"
parts = {}
for name in ["screen_lid", "keyboard_base"]:
    m = trimesh.load(part_dir / f"{name}.ply", process=False)
    m.apply_transform(T_cur)                        # same T -> seam preserved
    parts[name] = m

hand = trimesh.load(RUN_ROOT / "guidance_out" / f"{TOKEN}_hand.ply", process=False)
TIPS = {"thumb": 744, "index": 320, "middle": 443, "ring": 554, "pinky": 671}
tips = np.asarray(hand.vertices)[list(TIPS.values())]

report = {"scale_old": s_old, "scale_new": s_cur, "scale_ratio_new_over_old": s_cur / s_old,
          "num_target_points": int(len(tgt)), "mask": str(mask_path)}
for name, m in parts.items():
    dd, _ = cKDTree(np.asarray(m.vertices)).query(tips)
    report[f"fingertip_to_{name}_cm"] = {k: float(v * 100) for k, v in zip(TIPS, dd)}
    report[f"{name}_min_cm"], report[f"{name}_mean_cm"] = float(dd.min() * 100), float(dd.mean() * 100)
    print(f"[{name}] min={dd.min()*100:.2f}cm mean={dd.mean()*100:.2f}cm")

lid_min = report["screen_lid_min_cm"]
report["decision"] = ("PASS_UNDER_12P5CM_PROCEED_TO_BOUNDED_GATE_C" if lid_min <= 12.5
                      else "FAIL_FREEZE_AT_GATE_A_PLUS_B_MOVE_TO_ABOX01")
DECISION_JSON.write_text(json.dumps(report, indent=2))
print("[DECISION]", report["decision"])

# ---------- 5. visual ----------
def col(m, c):
    m = m.copy(); m.visual.vertex_colors = c; return m
scene = trimesh.Scene()
scene.add_geometry(col(parts["screen_lid"], [80, 140, 255, 255]), node_name="screen_lid_blue")
scene.add_geometry(col(parts["keyboard_base"], [80, 220, 120, 255]), node_name="keyboard_base_green")
scene.add_geometry(col(hand, [255, 80, 80, 255]), node_name="hand_red")
scene.export(V02 / "visuals" / f"{TOKEN}_v0_2_masked_realign_scene.glb")
trimesh.PointCloud(tgt).export(V02 / "outputs" / f"{TOKEN}_object_only_moge_target.ply")
print("[OK] scene + target cloud written")
