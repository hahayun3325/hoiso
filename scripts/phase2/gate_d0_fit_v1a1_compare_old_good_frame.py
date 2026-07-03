from pathlib import Path
import json
import trimesh
import numpy as np

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit_v1_getting_unstuck"
OLD_FIT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit"
ACTIVE = CASE_ROOT / "integrated_gates/gate_a_part_repair/active_clean_parts"

OUT_VIS = FIT / "visuals"
OUT_MET = FIT / "metrics"
OUT_VIS.mkdir(parents=True, exist_ok=True)
OUT_MET.mkdir(parents=True, exist_ok=True)

def load_mesh(path):
    obj = trimesh.load(path, force=None, process=False)
    if isinstance(obj, trimesh.Scene):
        geoms = [g for g in obj.geometry.values() if hasattr(g, "vertices") and len(g.vertices) > 0]
        return trimesh.util.concatenate(geoms)
    return obj

def colorize(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = rgba
    return m

def mesh_info(mesh):
    b = np.asarray(mesh.bounds)
    return {
        "num_vertices": int(len(mesh.vertices)),
        "num_faces": int(len(mesh.faces)),
        "bbox_min": b[0].tolist(),
        "bbox_max": b[1].tolist(),
        "bbox_extent": (b[1] - b[0]).tolist(),
        "center": mesh.centroid.tolist()
    }

# Try to load the old standalone fitter manifest.
old_manifest = OLD_FIT / "metrics/standalone_fitter_input_manifest.json"
if not old_manifest.exists():
    raise FileNotFoundError(f"Cannot find old v0 dry-run manifest: {old_manifest}")

m = json.loads(old_manifest.read_text())
paths = {k: Path(v["path"]) for k, v in m["paths"].items() if v.get("exists")}

hand_old = load_mesh(paths["guidance_hand"])

# Old active clean parts are the shared-frame engineering seed.
screen_old = load_mesh(ACTIVE / "screen.ply")
base_old = load_mesh(ACTIVE / "keyboard_base.ply")
hinge_old = load_mesh(ACTIVE / "hinge.ply")

# New fitted objects.
lid_fit = load_mesh(FIT / "outputs/lid_fitted_v1.ply")
base_fit = load_mesh(FIT / "outputs/base_fitted_v1.ply")

scene = trimesh.Scene()

# Old good frame: colored strongly.
scene.add_geometry(colorize(screen_old, [0, 0, 255, 90]), node_name="OLD_active_screen_blue")
scene.add_geometry(colorize(base_old, [255, 0, 255, 90]), node_name="OLD_active_base_magenta")
scene.add_geometry(colorize(hinge_old, [255, 180, 0, 160]), node_name="OLD_active_hinge_yellow")
scene.add_geometry(colorize(hand_old, [0, 255, 0, 120]), node_name="OLD_guidance_hand_green")

# New fitted frame: gray/cyan overlay.
scene.add_geometry(colorize(lid_fit, [0, 255, 255, 90]), node_name="NEW_fit_v1_lid_cyan")
scene.add_geometry(colorize(base_fit, [120, 120, 120, 90]), node_name="NEW_fit_v1_base_gray")

out_glb = OUT_VIS / "fit_v1a1_old_good_vs_fit_v1_frame_compare.glb"
scene.export(out_glb)

report = {
    "case_id": "alapuse01",
    "stage": "Gate D-0 fit v1a1 old-good-frame comparison",
    "old_manifest": str(old_manifest),
    "old_hand_path": str(paths["guidance_hand"]),
    "scene": str(out_glb),
    "mesh_info": {
        "old_hand": mesh_info(hand_old),
        "old_screen": mesh_info(screen_old),
        "old_base": mesh_info(base_old),
        "fit_v1_lid": mesh_info(lid_fit),
        "fit_v1_base": mesh_info(base_fit)
    },
    "decision_rule": {
        "old_frame_good": "old hand and active parts show plausible hand-laptop relation",
        "fit_frame_bad": "fit_v1 objects moved into a different frame or wrong relative pose",
        "next": "run v1b in old shared frame, not in raw MoGe frame"
    }
}

out_json = OUT_MET / "fit_v1a1_old_good_vs_fit_v1_frame_compare.json"
out_json.write_text(json.dumps(report, indent=2))

print("[OK] wrote", out_glb)
print("[OK] wrote", out_json)
print(json.dumps(report, indent=2)[:3000])
