from pathlib import Path
import argparse
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT_ROOT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit"
MANIFEST = FIT_ROOT / "metrics/standalone_fitter_input_manifest.json"
ACTIVE = CASE_ROOT / "integrated_gates/gate_a_part_repair/active_clean_parts"
CONTACT_TARGET = CASE_ROOT / "integrated_gates/gate_d_contact_scorer_v0/outputs/verified_contact_patch_target_v0.json"

OUT = CASE_ROOT / "integrated_gates/gate_c_v3_3_manual_top_lid_check"
OUT_METRICS = OUT / "metrics"
OUT_VIS = OUT / "visuals"
OUT_METRICS.mkdir(parents=True, exist_ok=True)
OUT_VIS.mkdir(parents=True, exist_ok=True)

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

def dist_stats(points, mesh):
    verts = np.asarray(mesh.vertices, dtype=float)
    d, idx = cKDTree(verts).query(points, k=1)
    return {
        "min": float(d.min()),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "p10": float(np.percentile(d, 10)),
        "mean": float(d.mean()),
        "max": float(d.max()),
        "within_5mm": int((d <= 0.005).sum()),
        "within_10mm": int((d <= 0.010).sum()),
        "within_20mm": int((d <= 0.020).sum()),
        "nearest_indices": idx.astype(int).tolist()
    }

ap = argparse.ArgumentParser()
ap.add_argument("--top-lid-component-idx", type=int, default=1,
                help="screen component index sorted by area. Based on v3.2, 1 is likely true top-lid; adjust after visual check.")
args = ap.parse_args()

data = json.loads(MANIFEST.read_text())
paths = {k: Path(v["path"]) for k, v in data["paths"].items() if v["exists"]}

target = json.loads(CONTACT_TARGET.read_text())
patch_hand_pts = np.asarray(target["hand_patch_points"], dtype=float)

screen = load_mesh(ACTIVE / "screen.ply")
base = load_mesh(ACTIVE / "keyboard_base.ply")
hinge = load_mesh(ACTIVE / "hinge.ply")
hand = load_mesh(paths["guidance_hand"])

screen_components = list(screen.split(only_watertight=False))
screen_components = sorted(screen_components, key=lambda m: m.area, reverse=True)

if args.top_lid_component_idx >= len(screen_components):
    raise ValueError(f"Requested component {args.top_lid_component_idx}, but only {len(screen_components)} screen components exist.")

top_lid = screen_components[args.top_lid_component_idx]
wrong_nearest = screen_components[0]

top_lid_stats = dist_stats(patch_hand_pts, top_lid)
wrong_nearest_stats = dist_stats(patch_hand_pts, wrong_nearest)
all_screen_stats = dist_stats(patch_hand_pts, screen)

if top_lid_stats["within_20mm"] > 0:
    decision = "TOP_LID_CONTACT_POSSIBLE"
elif top_lid_stats["mean"] <= 0.05:
    decision = "TOP_LID_NEAR_CONTACT_UNCERTAIN"
else:
    decision = "TOP_LID_CONTACT_NOT_SUPPORTED_IN_CURRENT_FRAME"

result = {
    "case_id": "alapuse01",
    "stage": "Gate C v3.3 manual top-lid/screen component verification",
    "manual_top_lid_component_idx_sorted_by_area": args.top_lid_component_idx,
    "num_screen_components": len(screen_components),
    "top_lid_distance": top_lid_stats,
    "nearest_wrong_component_00_distance": wrong_nearest_stats,
    "all_screen_distance": all_screen_stats,
    "decision": decision,
    "interpretation": {
        "if_top_lid_far": "current hand/object frame supports base-like contact, not desired screen/top-lid contact",
        "if_top_lid_near": "manual top-lid target can replace the wrong v0 target"
    }
}

out_json = OUT_METRICS / "gate_c_v3_3_manual_top_lid_check.json"
out_json.write_text(json.dumps(result, indent=2))

scene = trimesh.Scene()
scene.add_geometry(colorize(hand, [0, 255, 0, 80]), node_name="guidance_hand_green")
scene.add_geometry(colorize(base, [255, 140, 0, 160]), node_name="keyboard_base_orange")
scene.add_geometry(colorize(hinge, [255, 0, 255, 220]), node_name="hinge_magenta")
scene.add_geometry(colorize(wrong_nearest, [0, 0, 255, 100]), node_name="screen_component_00_wrong_nearest_blue")
scene.add_geometry(colorize(top_lid, [0, 255, 255, 170]), node_name=f"manual_top_lid_component_{args.top_lid_component_idx}_cyan")

for i, p in enumerate(patch_hand_pts):
    scene.add_geometry(marker(p, 0.004, [255, 0, 0, 255]), node_name=f"hand_patch_red_{i:03d}")

out_glb = OUT_VIS / "gate_c_v3_3_manual_top_lid_check.glb"
scene.export(out_glb)

print("[OK] wrote", out_json)
print("[OK] wrote", out_glb)
print("[DECISION]", decision)
print(json.dumps(result, indent=2))
