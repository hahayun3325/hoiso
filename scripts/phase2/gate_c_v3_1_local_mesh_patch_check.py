from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT_ROOT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit"
MANIFEST = FIT_ROOT / "metrics/standalone_fitter_input_manifest.json"
ACTIVE = CASE_ROOT / "integrated_gates/gate_a_part_repair/active_clean_parts"

OUT = CASE_ROOT / "integrated_gates/gate_c_v3_1_local_mesh_patch"
OUT_METRICS = OUT / "metrics"
OUT_VIS = OUT / "visuals"
OUT_NOTES = OUT / "notes"

for p in [OUT_METRICS, OUT_VIS, OUT_NOTES]:
    p.mkdir(parents=True, exist_ok=True)

def load_mesh(path):
    obj = trimesh.load(path, force=None, process=False)
    if isinstance(obj, trimesh.Scene):
        geoms = [
            g for g in obj.geometry.values()
            if hasattr(g, "vertices") and len(g.vertices) > 0
        ]
        return trimesh.util.concatenate(geoms)
    return obj

def colorize(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = rgba
    return m

def marker(center, radius, rgba):
    s = trimesh.creation.icosphere(subdivisions=2, radius=radius)
    s.apply_translation(np.asarray(center, dtype=float))
    s.visual.vertex_colors = rgba
    return s

data = json.loads(MANIFEST.read_text())
paths = {k: Path(v["path"]) for k, v in data["paths"].items() if v["exists"]}

screen = load_mesh(ACTIVE / "screen.ply")
base = load_mesh(ACTIVE / "keyboard_base.ply")
hinge = load_mesh(ACTIVE / "hinge.ply")
hand = load_mesh(paths["guidance_hand"])

screen_pts = np.asarray(screen.vertices, dtype=float)
hand_pts = np.asarray(hand.vertices, dtype=float)

tree = cKDTree(screen_pts)
d, idx = tree.query(hand_pts, k=1)

# Local contact candidates: closest hand vertices to the screen.
thresholds = [0.005, 0.010, 0.020, 0.030]
patch_info = {}

for th in thresholds:
    ids = np.where(d <= th)[0]
    patch_info[f"within_{int(th*1000)}mm"] = {
        "count": int(len(ids)),
        "ratio": float(len(ids) / max(len(hand_pts), 1)),
        "vertex_indices_first50": ids[:50].astype(int).tolist()
    }

# Use closest 1% of hand vertices as a robust patch.
k = max(20, int(0.01 * len(hand_pts)))
nearest_ids = np.argsort(d)[:k]
nearest_screen_ids = idx[nearest_ids]

patch_hand_pts = hand_pts[nearest_ids]
patch_screen_pts = screen_pts[nearest_screen_ids]

centroid_hand = patch_hand_pts.mean(axis=0)
centroid_screen = patch_screen_pts.mean(axis=0)

result = {
    "case_id": "alapuse01",
    "stage": "Gate C v3.1 local hand-mesh patch verification",
    "object_seed": "v0 dry-run active clean parts",
    "reason": "HaMeR keypoints failed, but global hand-screen distance is close",
    "global_hand_to_screen": {
        "min": float(d.min()),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "p10": float(np.percentile(d, 10)),
        "mean": float(d.mean())
    },
    "threshold_patch_counts": patch_info,
    "nearest_1_percent_patch": {
        "num_vertices": int(len(nearest_ids)),
        "hand_vertex_indices_first100": nearest_ids[:100].astype(int).tolist(),
        "mean_distance": float(d[nearest_ids].mean()),
        "max_distance": float(d[nearest_ids].max()),
        "hand_patch_centroid": centroid_hand.tolist(),
        "screen_patch_centroid": centroid_screen.tolist(),
        "centroid_distance": float(np.linalg.norm(centroid_hand - centroid_screen))
    },
    "decision_rule": {
        "pass": "nearest patch is visually on intended contact fingers and screen surface",
        "partial": "patch is near hand-screen contact but finger identity remains uncertain",
        "fail": "patch is on wrist/palm/wrong hand region or wrong object part"
    },
    "preliminary_decision": "VISUAL_CHECK_REQUIRED"
}

# Create marker scene.
scene = trimesh.Scene()
scene.add_geometry(colorize(screen, [0, 0, 255, 140]), node_name="active_screen_blue")
scene.add_geometry(colorize(base, [255, 140, 0, 170]), node_name="active_keyboard_base_orange")
scene.add_geometry(colorize(hinge, [255, 0, 255, 220]), node_name="active_hinge_magenta")
scene.add_geometry(colorize(hand, [0, 255, 0, 90]), node_name="guidance_hand_green")

# Add many small red markers for closest hand patch.
for i, p in enumerate(patch_hand_pts[:200]):
    scene.add_geometry(marker(p, 0.0035, [255, 0, 0, 255]), node_name=f"hand_patch_red_{i:03d}")

# Add blue markers for nearest screen points.
for i, p in enumerate(patch_screen_pts[:200]):
    scene.add_geometry(marker(p, 0.003, [0, 0, 255, 255]), node_name=f"screen_patch_blue_{i:03d}")

# Add centroid markers.
scene.add_geometry(marker(centroid_hand, 0.009, [255, 0, 0, 255]), node_name="hand_patch_centroid_red")
scene.add_geometry(marker(centroid_screen, 0.009, [0, 0, 255, 255]), node_name="screen_patch_centroid_blue")

out_json = OUT_METRICS / "gate_c_v3_1_local_mesh_patch_check.json"
out_glb = OUT_VIS / "gate_c_v3_1_local_mesh_patch_markers.glb"

out_json.write_text(json.dumps(result, indent=2))
scene.export(out_glb)

print("[OK] wrote", out_json)
print("[OK] wrote", out_glb)
print(json.dumps(result, indent=2)[:3000])
