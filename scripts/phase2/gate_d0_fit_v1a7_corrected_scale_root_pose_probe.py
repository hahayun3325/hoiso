from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
V1A5 = FIT / "scale_frame_audit_v1a5"
V1A6 = FIT / "hand_scale_provenance_audit_v1a6"
V1A7 = FIT / "corrected_scale_root_pose_probe_v1a7"

SEL_RUN = Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse01_selector_v41_refined_pipeline")
ACTIVE = CASE_ROOT / "integrated_gates/gate_a_part_repair/active_clean_parts"

VIS = V1A7 / "visuals"
MET = V1A7 / "metrics"
OUT = V1A7 / "outputs"
for p in [VIS, MET, OUT]:
    p.mkdir(parents=True, exist_ok=True)

def load_mesh(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    obj = trimesh.load(path, force=None, process=False)
    if isinstance(obj, trimesh.Scene):
        geoms = [g for g in obj.geometry.values() if hasattr(g, "vertices") and len(g.vertices) > 0]
        if not geoms:
            raise ValueError(f"empty scene: {path}")
        return trimesh.util.concatenate(geoms)
    return obj

def colorize(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = rgba
    return m

def bbox_info(mesh):
    b = np.asarray(mesh.bounds, dtype=float)
    ext = b[1] - b[0]
    return {
        "bbox_min": b[0].tolist(),
        "bbox_max": b[1].tolist(),
        "extent_xyz": ext.tolist(),
        "xy_max_extent": float(ext[:2].max()),
        "max_extent": float(ext.max()),
        "center": np.asarray(mesh.centroid).tolist(),
        "num_vertices": int(len(mesh.vertices)),
        "num_faces": int(len(mesh.faces))
    }

def scale_about(mesh, center, scale):
    out = mesh.copy()
    v = np.asarray(out.vertices)
    out.vertices = (v - center) * scale + center
    return out

def translate(mesh, vec):
    out = mesh.copy()
    out.apply_translation(vec)
    return out

def sample(mesh, n=10000, seed=0):
    rng = np.random.default_rng(seed)
    if len(mesh.faces) > 0:
        pts, _ = trimesh.sample.sample_surface(mesh, n)
        return pts
    v = np.asarray(mesh.vertices)
    if len(v) <= n:
        return v
    return v[rng.choice(len(v), n, replace=False)]

def nearest_stats(A, B):
    tree = cKDTree(B)
    d, idx = tree.query(A, k=1)
    return d, idx, {
        "min": float(np.min(d)),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "p10": float(np.percentile(d, 10)),
        "mean": float(np.mean(d)),
        "within_02": int(np.sum(d < 0.02)),
        "within_05": int(np.sum(d < 0.05))
    }

def export_scene(name, hand, screen, base, hinge):
    scene = trimesh.Scene()
    scene.add_geometry(colorize(hand, [0, 255, 0, 130]), node_name="hand_green")
    scene.add_geometry(colorize(screen, [0, 190, 255, 150]), node_name="screen_lid_cyan")
    scene.add_geometry(colorize(base, [255, 0, 255, 140]), node_name="base_magenta")
    scene.add_geometry(colorize(hinge, [255, 180, 0, 180]), node_name="hinge_yellow")
    out = VIS / f"{name}.glb"
    scene.export(out)
    return str(out)

aligned_mano = load_mesh(SEL_RUN / "aligned_mano/alapuse01_hamer_aligned_mano.ply")
guidance_hand = load_mesh(SEL_RUN / "guidance_out/alapuse01_hand.ply")

screen = load_mesh(ACTIVE / "screen.ply")
base = load_mesh(ACTIVE / "keyboard_base.ply")
hinge = load_mesh(ACTIVE / "hinge.ply")

v1a5_report = json.loads((V1A5 / "metrics/fit_v1a5_scale_frame_audit.json").read_text())
object_scale = float(v1a5_report["ratios"]["object_scale_to_depth_xy"])

# 1. Hand scale fix: aligned_mano -> guidance_hand bbox scale.
aligned_info = bbox_info(aligned_mano)
guidance_info = bbox_info(guidance_hand)
hand_scale = guidance_info["xy_max_extent"] / max(aligned_info["xy_max_extent"], 1e-12)

hand_scaled = scale_about(aligned_mano, np.asarray(aligned_mano.centroid), hand_scale)

# 2. Object scale fix: active object -> MoGe/mask depth XY scale.
obj_all = trimesh.util.concatenate([screen, base, hinge])
obj_center = np.asarray(obj_all.centroid)
screen_scaled = scale_about(screen, obj_center, object_scale)
base_scaled = scale_about(base, obj_center, object_scale)
hinge_scaled = scale_about(hinge, obj_center, object_scale)

# 3. Contact-closing translation options.
hand_v = np.asarray(hand_scaled.vertices)
screen_pts = sample(screen_scaled, n=12000, seed=1)
base_pts = sample(base_scaled, n=12000, seed=2)

d_hs, idx_hs, before_screen_stats = nearest_stats(hand_v, screen_pts)
_, _, before_base_stats = nearest_stats(hand_v, base_pts)

# Use the closest 10% hand vertices as local contact patch.
k = max(20, min(80, int(0.10 * len(hand_v))))
patch_ids = np.argsort(d_hs)[:k]
hand_patch = hand_v[patch_ids]
screen_patch = screen_pts[idx_hs[patch_ids]]

snap_vec_full = hand_patch.mean(axis=0) - screen_patch.mean(axis=0)

# Candidate translations:
# A: no translation
# B: full 3D object root translation to contact
# C: vertical-only translation, safer if z/up is consistent
# D: clipped root translation with max 8 cm, diagnostic for small repair feasibility
max_root = 0.08
snap_norm = float(np.linalg.norm(snap_vec_full))
snap_vec_clipped = snap_vec_full.copy()
if snap_norm > max_root:
    snap_vec_clipped = snap_vec_full / snap_norm * max_root

# Use vertical component as the axis with largest absolute snap component.
vertical_axis = int(np.argmax(np.abs(snap_vec_full)))
snap_vec_axis_only = np.zeros(3)
snap_vec_axis_only[vertical_axis] = snap_vec_full[vertical_axis]

candidates = {
    "A_scaled_hand_scaled_object_no_translation": np.zeros(3),
    "B_scaled_hand_scaled_object_full_root_snap_debug": snap_vec_full,
    "C_scaled_hand_scaled_object_axis_only_snap_debug": snap_vec_axis_only,
    "D_scaled_hand_scaled_object_clipped_8cm_root": snap_vec_clipped
}

scenes = {}
metrics = {}

for name, vec in candidates.items():
    s2 = translate(screen_scaled, vec)
    b2 = translate(base_scaled, vec)
    h2 = translate(hinge_scaled, vec)

    sp = sample(s2, n=12000, seed=3)
    bp = sample(b2, n=12000, seed=4)

    _, _, hand_to_screen = nearest_stats(hand_v, sp)
    _, _, hand_to_base = nearest_stats(hand_v, bp)

    scenes[name] = export_scene(name, hand_scaled, s2, b2, h2)

    metrics[name] = {
        "translation_vec": np.asarray(vec).tolist(),
        "translation_norm": float(np.linalg.norm(vec)),
        "hand_to_screen": hand_to_screen,
        "hand_to_base": hand_to_base
    }

# Export candidate meshes for the safest path.
hand_scaled.export(OUT / "hand_aligned_mano_scaled_to_guidance_bbox_v1a7.ply")
screen_scaled.export(OUT / "screen_object_scaled_v1a7.ply")
base_scaled.export(OUT / "base_object_scaled_v1a7.ply")
hinge_scaled.export(OUT / "hinge_object_scaled_v1a7.ply")

screen_clipped = translate(screen_scaled, snap_vec_clipped)
base_clipped = translate(base_scaled, snap_vec_clipped)
hinge_clipped = translate(hinge_scaled, snap_vec_clipped)

screen_clipped.export(OUT / "screen_v1a7_clipped_root_candidate.ply")
base_clipped.export(OUT / "base_v1a7_clipped_root_candidate.ply")
hinge_clipped.export(OUT / "hinge_v1a7_clipped_root_candidate.ply")

# Decision
decision = "VISUAL_CHECK_REQUIRED"
if metrics["D_scaled_hand_scaled_object_clipped_8cm_root"]["hand_to_screen"]["within_05"] > 20:
    decision = "CANDIDATE_D_SMALL_ROOT_TRANSLATION_NUMERIC_PASS_VISUAL_CHECK_REQUIRED"
elif metrics["B_scaled_hand_scaled_object_full_root_snap_debug"]["translation_norm"] > 0.12:
    decision = "FULL_ROOT_SNAP_TOO_LARGE_SCALE_FIX_NOT_ENOUGH"
else:
    decision = "CORRECTED_SCALE_FRAME_NEEDS_VISUAL_CHECK"

report = {
    "case_id": "alapuse01",
    "stage": "Gate D-0 fit v1a7 corrected-scale root-pose probe",
    "uses_gt": False,
    "object_scale_from_v1a5": object_scale,
    "hand_scale_aligned_mano_to_guidance": hand_scale,
    "before_contact": {
        "hand_to_screen": before_screen_stats,
        "hand_to_base": before_base_stats
    },
    "snap": {
        "snap_vec_full": snap_vec_full.tolist(),
        "snap_norm_full": snap_norm,
        "vertical_axis_by_abs_snap": vertical_axis,
        "snap_vec_axis_only": snap_vec_axis_only.tolist(),
        "snap_vec_clipped_8cm": snap_vec_clipped.tolist()
    },
    "candidate_metrics": metrics,
    "scenes": scenes,
    "outputs": {
        "hand_scaled": str(OUT / "hand_aligned_mano_scaled_to_guidance_bbox_v1a7.ply"),
        "screen_scaled": str(OUT / "screen_object_scaled_v1a7.ply"),
        "base_scaled": str(OUT / "base_object_scaled_v1a7.ply"),
        "hinge_scaled": str(OUT / "hinge_object_scaled_v1a7.ply"),
        "screen_clipped_root_candidate": str(OUT / "screen_v1a7_clipped_root_candidate.ply"),
        "base_clipped_root_candidate": str(OUT / "base_v1a7_clipped_root_candidate.ply"),
        "hinge_clipped_root_candidate": str(OUT / "hinge_v1a7_clipped_root_candidate.ply")
    },
    "decision": decision,
    "decision_rule": {
        "PASS_TO_V1B": "clipped 8cm or smaller root correction visually puts fingers near lid/screen without wrong base penetration",
        "PARTIAL": "full root snap works but clipped/small root does not",
        "FAIL": "corrected hand/object scale still gives wrong contact or large residual gap"
    },
    "next_step": "inspect v1a7 scenes and decide whether to create v1b"
}

out = MET / "fit_v1a7_corrected_scale_root_pose_probe.json"
out.write_text(json.dumps(report, indent=2))

print("[OK] wrote", out)
print("[decision]", decision)
print("[object_scale]", object_scale)
print("[hand_scale]", hand_scale)
print("[snap_norm_full]", snap_norm)
for k, v in metrics.items():
    print("\n==", k)
    print("translation_norm:", v["translation_norm"])
    print("hand_to_screen:", v["hand_to_screen"])
    print("hand_to_base:", v["hand_to_base"])
print("\n[scenes]")
for k, v in scenes.items():
    print(k, "->", v)
