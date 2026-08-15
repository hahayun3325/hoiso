from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
OUT = CASE_ROOT / "gate_d0_object_repair"
OUT_OUT = OUT / "outputs"
OUT_VIS = OUT / "visuals"
OUT_MET = OUT / "metrics"
OUT_OUT.mkdir(parents=True, exist_ok=True)
OUT_VIS.mkdir(parents=True, exist_ok=True)
OUT_MET.mkdir(parents=True, exist_ok=True)

# Candidate source object: current selector-v41 / Phase2 object
src_candidates = [
    CASE_ROOT / "input/final_object.ply",
    CASE_ROOT / "part_meshes_partfield_v2_vmap/part_scene.glb",
    CASE_ROOT / "gt_reference/selector_v41_aligned_diagnostic/aligned_pred_object_selector_v41.ply",
]
tgt_candidates = [
    CASE_ROOT / "gt_reference/selected/gt_object_mesh.ply",
]
hand_candidates = [
    CASE_ROOT / "input/final_hand.ply",
    CASE_ROOT / "gt_reference/selector_v41_aligned_diagnostic/aligned_pred_hand_selector_v41.ply",
]

def first_existing(paths):
    for p in paths:
        if p.exists():
            return p
    raise FileNotFoundError("None exists:\n" + "\n".join(map(str, paths)))

src_path = first_existing(src_candidates)
tgt_path = first_existing(tgt_candidates)
hand_path = first_existing(hand_candidates)

def load_mesh(path):
    m = trimesh.load(path, force="mesh")
    if isinstance(m, trimesh.Scene):
        m = trimesh.util.concatenate([g for g in m.geometry.values()])
    if len(m.vertices) == 0:
        raise ValueError(f"empty mesh: {path}")
    return m

src = load_mesh(src_path)
tgt = load_mesh(tgt_path)
hand = load_mesh(hand_path)

def sample_points(mesh, n=5000):
    n = min(n, max(100, len(mesh.vertices)))
    if len(mesh.faces) > 0:
        pts = mesh.sample(n)
    else:
        idx = np.random.choice(len(mesh.vertices), size=n, replace=len(mesh.vertices) < n)
        pts = mesh.vertices[idx]
    return np.asarray(pts, dtype=np.float64)

def umeyama(src_pts, dst_pts, with_scale=True):
    src_mean = src_pts.mean(axis=0)
    dst_mean = dst_pts.mean(axis=0)
    X = src_pts - src_mean
    Y = dst_pts - dst_mean

    cov = (Y.T @ X) / len(src_pts)
    U, D, Vt = np.linalg.svd(cov)

    S = np.eye(3)
    if np.linalg.det(U @ Vt) < 0:
        S[-1, -1] = -1

    R = U @ S @ Vt

    if with_scale:
        var = (X ** 2).sum() / len(src_pts)
        scale = np.trace(np.diag(D) @ S) / max(var, 1e-12)
    else:
        scale = 1.0

    t = dst_mean - scale * R @ src_mean

    T = np.eye(4)
    T[:3, :3] = scale * R
    T[:3, 3] = t
    return T

src_pts0 = sample_points(src, 8000)
tgt_pts = sample_points(tgt, 8000)

# Initialize by bbox scale + centroid
src_center = src_pts0.mean(axis=0)
tgt_center = tgt_pts.mean(axis=0)
src_diag = np.linalg.norm(src.bounds[1] - src.bounds[0])
tgt_diag = np.linalg.norm(tgt.bounds[1] - tgt.bounds[0])
init_scale = tgt_diag / max(src_diag, 1e-12)

T_total = np.eye(4)
T_total[:3, :3] *= init_scale
T_total[:3, 3] = tgt_center - init_scale * src_center

tree = cKDTree(tgt_pts)

for _ in range(20):
    pts_h = np.c_[src_pts0, np.ones(len(src_pts0))]
    moved = (T_total @ pts_h.T).T[:, :3]
    d, idx = tree.query(moved, k=1)
    keep = d < np.percentile(d, 85)
    if keep.sum() < 20:
        keep = np.ones_like(d, dtype=bool)
    T_delta = umeyama(moved[keep], tgt_pts[idx[keep]], with_scale=True)
    T_total = T_delta @ T_total

src_repaired = src.copy()
src_repaired.apply_transform(T_total)

src_repaired_path = OUT_OUT / "object_repaired_oracle_similarity_to_gt.ply"
src_repaired.export(src_repaired_path)

# Apply same transform to part meshes if available
part_dir = CASE_ROOT / "part_meshes_partfield_v2_vmap"
part_out = OUT_OUT / "parts_repaired_oracle_similarity_to_gt"
part_out.mkdir(exist_ok=True)

for name in ["screen", "keyboard_base", "hinge", "residual_uncertain"]:
    p = part_dir / f"{name}.ply"
    if p.exists():
        pm = load_mesh(p)
        pm.apply_transform(T_total)
        pm.export(part_out / f"{name}.ply")

def nn_mean(a_mesh, b_mesh):
    a = sample_points(a_mesh, 5000)
    b = sample_points(b_mesh, 5000)
    tr = cKDTree(b)
    d, _ = tr.query(a)
    return float(d.mean()), float(np.percentile(d, 5)), float(np.percentile(d, 50))

before_mean, before_p5, before_p50 = nn_mean(src, tgt)
after_mean, after_p5, after_p50 = nn_mean(src_repaired, tgt)

metrics = {
    "source_object": str(src_path),
    "target_gt_object": str(tgt_path),
    "hand_for_visual": str(hand_path),
    "status": "ORACLE_DIAGNOSTIC_NOT_FINAL_METHOD",
    "before": {"object_to_gt_nn_mean": before_mean, "p5": before_p5, "p50": before_p50},
    "after": {"object_to_gt_nn_mean": after_mean, "p5": after_p5, "p50": after_p50},
    "transform_4x4": T_total.tolist(),
    "output_object": str(src_repaired_path),
    "output_parts_dir": str(part_out)
}

(OUT_MET / "gate_d0_object_repair_oracle_diagnostic_metrics.json").write_text(json.dumps(metrics, indent=2))

# Scene: hand green, original object blue, repaired object gray, GT object transparent-ish gray
scene = trimesh.Scene()
hand.visual.vertex_colors = [0, 255, 0, 180]
src.visual.vertex_colors = [0, 0, 255, 100]
src_repaired.visual.vertex_colors = [80, 80, 80, 220]
tgt.visual.vertex_colors = [180, 180, 180, 80]

scene.add_geometry(src, node_name="original_pred_object_blue")
scene.add_geometry(src_repaired, node_name="repaired_pred_object_dark_gray")
scene.add_geometry(tgt, node_name="gt_object_light_gray")
scene.add_geometry(hand, node_name="pred_or_aligned_hand_green")

scene.export(OUT_VIS / "gate_d0_object_repair_oracle_diagnostic.glb")

print("[OK] wrote", src_repaired_path)
print("[OK] wrote", OUT_VIS / "gate_d0_object_repair_oracle_diagnostic.glb")
print(json.dumps(metrics, indent=2)[:2000])
