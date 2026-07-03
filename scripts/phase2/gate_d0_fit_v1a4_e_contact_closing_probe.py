from pathlib import Path
import json
import math
import numpy as np
import trimesh
from scipy.spatial import cKDTree

def to_jsonable(obj):
    import numpy as np
    import trimesh
    if isinstance(obj, trimesh.Trimesh):
        return {
            "_type": "Trimesh",
            "num_vertices": int(len(obj.vertices)),
            "num_faces": int(len(obj.faces)),
            "bounds": obj.bounds.tolist()
        }
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
V1A4 = FIT / "e_candidate_contact_closing_v1a4"
VIS = V1A4 / "visuals"
MET = V1A4 / "metrics"
OUT = V1A4 / "outputs"
VIS.mkdir(parents=True, exist_ok=True)
MET.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

SEL_RUN = Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse01_selector_v41_refined_pipeline")
ACTIVE = CASE_ROOT / "integrated_gates/gate_a_part_repair/active_clean_parts"

paths = {
    "hand": SEL_RUN / "aligned_mano/alapuse01_hamer_aligned_mano.ply",
    "screen": ACTIVE / "screen.ply",
    "base": ACTIVE / "keyboard_base.ply",
    "hinge": ACTIVE / "hinge.ply"
}

def load_mesh(path):
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

def sample(mesh, n=8000, seed=0):
    rng = np.random.default_rng(seed)
    if len(mesh.faces) > 0:
        pts, _ = trimesh.sample.sample_surface(mesh, n)
        return pts
    v = np.asarray(mesh.vertices)
    if len(v) <= n:
        return v
    return v[rng.choice(len(v), size=n, replace=False)]

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

def pca_axis(points):
    c = points.mean(axis=0)
    X = points - c
    _, _, vt = np.linalg.svd(X, full_matrices=False)
    return c, vt[0] / max(np.linalg.norm(vt[0]), 1e-12)

def rotate_about_axis(points, pivot, axis, angle_rad):
    axis = axis / max(np.linalg.norm(axis), 1e-12)
    x, y, z = axis
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    C = 1.0 - c
    R = np.array([
        [c + x*x*C, x*y*C - z*s, x*z*C + y*s],
        [y*x*C + z*s, c + y*y*C, y*z*C - x*s],
        [z*x*C - y*s, z*y*C + x*s, c + z*z*C]
    ], dtype=np.float64)
    return (points - pivot) @ R.T + pivot

def transform_mesh_vertices(mesh, verts):
    out = mesh.copy()
    out.vertices = verts
    return out

def translate_mesh(mesh, vec):
    out = mesh.copy()
    out.apply_translation(vec)
    return out

def export_scene(name, hand, screen, base, hinge, extra=None):
    scene = trimesh.Scene()
    scene.add_geometry(colorize(screen, [0, 180, 255, 150]), node_name="screen_lid_cyan")
    scene.add_geometry(colorize(base, [255, 0, 255, 135]), node_name="keyboard_base_magenta")
    scene.add_geometry(colorize(hinge, [255, 180, 0, 180]), node_name="hinge_yellow")
    scene.add_geometry(colorize(hand, [0, 255, 0, 120]), node_name="hand_green")
    if extra:
        for k, g in extra.items():
            scene.add_geometry(g, node_name=k)
    out = VIS / f"{name}.glb"
    scene.export(out)
    return str(out)

hand = load_mesh(paths["hand"])
screen = load_mesh(paths["screen"])
base = load_mesh(paths["base"])
hinge = load_mesh(paths["hinge"])

hand_v = np.asarray(hand.vertices)
screen_pts = sample(screen, 10000, seed=1)
base_pts = sample(base, 10000, seed=2)
hinge_v = np.asarray(hinge.vertices)

# Use closest hand vertices to screen as a local contact patch.
d_hs, idx_hs, h2s_stats = nearest_stats(hand_v, screen_pts)
patch_k = min(80, max(20, int(0.10 * len(hand_v))))
patch_ids = np.argsort(d_hs)[:patch_k]
hand_patch = hand_v[patch_ids]
screen_patch = screen_pts[idx_hs[patch_ids]]

hand_center = hand_patch.mean(axis=0)
screen_center = screen_patch.mean(axis=0)
snap_vec = hand_center - screen_center
snap_norm = float(np.linalg.norm(snap_vec))

# Original scene.
original_scene = export_scene("E_original", hand, screen, base, hinge)

# Whole-object snap: physically preserves object structure but moves whole laptop.
whole_screen = translate_mesh(screen, snap_vec)
whole_base = translate_mesh(base, snap_vec)
whole_hinge = translate_mesh(hinge, snap_vec)
whole_scene = export_scene("E_whole_object_snap_to_hand_patch", hand, whole_screen, whole_base, whole_hinge)

# Screen-only debug snap: not physically valid, but tests whether the lid itself can meet the hand.
screen_only = translate_mesh(screen, snap_vec)
screen_only_scene = export_scene("E_screen_only_snap_debug_not_final", hand, screen_only, base, hinge)

# Hinge rotation search: base fixed, screen rotates around hinge PCA axis.
pivot, axis = pca_axis(hinge_v)
best = None
angle_rows = []

for deg in np.linspace(-65, 65, 53):
    angle = math.radians(float(deg))
    rot_v = rotate_about_axis(np.asarray(screen.vertices), pivot, axis, angle)
    rot_screen = transform_mesh_vertices(screen, rot_v)

    rot_pts = sample(rot_screen, 6000, seed=3)
    d_patch, _, patch_stats = nearest_stats(hand_patch, rot_pts)

    # Hinge connection: rotated screen should stay near hinge/base.
    screen_near_hinge, _, sh_stats = nearest_stats(rot_pts, hinge_v)
    base_near_screen, _, bs_stats = nearest_stats(hinge_v, rot_pts)

    # Lower is better.
    score = (
        patch_stats["p5"]
        + 0.5 * patch_stats["mean"]
        + 1.0 * sh_stats["p5"]
        + 0.5 * bs_stats["p5"]
    )

    row = {
        "angle_deg": float(deg),
        "score_lower_better": float(score),
        "contact_patch_to_screen": patch_stats,
        "screen_to_hinge": sh_stats,
        "hinge_to_screen": bs_stats
    }
    angle_rows.append(row)

    if best is None or score < best["score_lower_better"]:
        best = row
        best["screen_mesh"] = rot_screen

best_screen = best.pop("screen_mesh")
best_hinge_scene = export_scene("E_best_hinge_rotation_contact_closing", hand, best_screen, base, hinge)

# Metrics after whole-object and screen-only snap.
whole_pts = sample(whole_screen, 6000, seed=4)
screen_only_pts = sample(screen_only, 6000, seed=5)

_, _, whole_stats = nearest_stats(hand_patch, whole_pts)
_, _, screen_only_stats = nearest_stats(hand_patch, screen_only_pts)

# Export selected output meshes for next step.
best_screen.export(OUT / "screen_v1a4_best_hinge_rotation.ply")
base.export(OUT / "base_v1a4_fixed_from_E.ply")
hinge.export(OUT / "hinge_v1a4_fixed_from_E.ply")
hand.export(OUT / "hand_v1a4_E_aligned_mano.ply")

decision = "UNDECIDED_VISUAL_CHECK_REQUIRED"
if best["contact_patch_to_screen"]["mean"] < 0.04:
    decision = "HINGE_CONTACT_CLOSING_NUMERIC_PASS_VISUAL_CHECK_REQUIRED"
elif snap_norm < 0.08:
    decision = "SMALL_SNAP_POSSIBLE_BUT_HINGE_NOT_ENOUGH"
else:
    decision = "LARGE_GAP_E_STRUCTURAL_ONLY"

report = {
    "case_id": "alapuse01",
    "stage": "Gate D-0 fit v1a4 E-candidate contact-closing diagnostic",
    "uses_gt": False,
    "inputs": {k: str(v) for k, v in paths.items()},
    "original_hand_to_screen_all_vertices": h2s_stats,
    "contact_patch": {
        "num_vertices": int(len(hand_patch)),
        "hand_patch_center": hand_center.tolist(),
        "screen_patch_center": screen_center.tolist(),
        "snap_vector_screen_to_hand": snap_vec.tolist(),
        "snap_norm_m": snap_norm
    },
    "scenes": {
        "original": original_scene,
        "whole_object_snap": whole_scene,
        "screen_only_debug_snap_not_final": screen_only_scene,
        "best_hinge_rotation": best_hinge_scene
    },
    "whole_object_snap_contact_patch_to_screen": whole_stats,
    "screen_only_snap_contact_patch_to_screen": screen_only_stats,
    "best_hinge_rotation": best,
    "all_hinge_angle_rows": angle_rows,
    "decision": decision,
    "decision_rule": {
        "PASS_FOR_V1B": "best hinge/contact scene visually puts right fingers near lid/screen without moving base into wrong place",
        "PARTIAL": "whole-object or screen-only snap shows possible contact but hinge rotation cannot do it yet",
        "FAIL": "large gap or all repairs remain wrong"
    },
    "next_step": "open all v1a4 scenes and choose whether E can become v1b seed"
}

out_json = MET / "fit_v1a4_e_contact_closing_report.json"
out_json.write_text(json.dumps(report, indent=2, default=to_jsonable))

print("[OK] wrote", out_json)
print("[decision]", decision)
print("[snap_norm_m]", snap_norm)
print("[original h2screen]", h2s_stats)
print("[whole snap]", whole_stats)
print("[screen-only snap]", screen_only_stats)
print("[best hinge]", best)
for k, v in report["scenes"].items():
    print(k, "->", v)
