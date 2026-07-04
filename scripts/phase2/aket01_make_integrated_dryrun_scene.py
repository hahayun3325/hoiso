from pathlib import Path
import trimesh
import json

DATA = Path("/home/fredcui/foho_phase0")
CASE_ROOT = DATA / "phase2_gateA_part_recon/cases/aket01"
AKET = CASE_ROOT / "integrated_gates/positive_control_aket01"
ACTIVE = AKET / "active_parts_v0"
SEL_RUN = DATA / "phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_aket01_selector_v41_refined_pipeline"

VIS = AKET / "visuals"
MET = AKET / "metrics"
VIS.mkdir(parents=True, exist_ok=True)
MET.mkdir(parents=True, exist_ok=True)

def load_mesh(p):
    p = Path(p)
    if not p.exists():
        raise FileNotFoundError(p)
    obj = trimesh.load(p, process=False)
    if isinstance(obj, trimesh.Scene):
        geoms = [g for g in obj.geometry.values() if hasattr(g, "vertices") and len(g.vertices) > 0]
        return trimesh.util.concatenate(geoms)
    return obj

def colorize(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = rgba
    return m

scene = trimesh.Scene()

# Load hand.
hand_candidates = [
    SEL_RUN / "aligned_mano/aket01_hamer_aligned_mano.ply",
    SEL_RUN / "guidance_out/aket01_hand.ply",
]
hand_path = next((p for p in hand_candidates if p.exists()), None)
if hand_path:
    scene.add_geometry(colorize(load_mesh(hand_path), [0, 255, 0, 130]), node_name="hand_green")

# Load object.
obj_candidates = [
    SEL_RUN / "guidance_out/aket01_obj.ply",
]
obj_path = next((p for p in obj_candidates if p.exists()), None)
if obj_path:
    scene.add_geometry(colorize(load_mesh(obj_path), [255, 255, 255, 70]), node_name="raw_object_white")

colors = [
    [0, 180, 255, 150],
    [255, 0, 255, 150],
    [255, 180, 0, 180],
    [0, 0, 255, 120],
    [255, 0, 0, 120],
]
part_paths = sorted(ACTIVE.glob("*.ply"))
for i, p in enumerate(part_paths):
    scene.add_geometry(colorize(load_mesh(p), colors[i % len(colors)]), node_name=f"part_{p.stem}")

out = VIS / "aket01_integrated_dryrun_scene.glb"
scene.export(out)

report = {
    "case_id": "aket01",
    "stage": "integrated dry-run scene",
    "hand_path": str(hand_path) if hand_path else None,
    "object_path": str(obj_path) if obj_path else None,
    "part_paths": [str(p) for p in part_paths],
    "visual": str(out),
    "decision": "VISUAL_REVIEW_REQUIRED"
}
(MET / "aket01_integrated_dryrun_scene_report.json").write_text(json.dumps(report, indent=2))

print("[OK] visual:", out)
print(json.dumps(report, indent=2))
