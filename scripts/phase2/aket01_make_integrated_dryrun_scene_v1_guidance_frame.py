from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

DATA = Path("/home/fredcui/foho_phase0")
CASE_ROOT = DATA / "phase2_gateA_part_recon/cases/aket01"
AKET = CASE_ROOT / "integrated_gates/positive_control_aket01"
ACTIVE = AKET / "active_parts_v0"
SEL_RUN = DATA / "phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_aket01_selector_v41_refined_pipeline"
V1 = AKET / "dryrun_v1_guidance_frame"

VIS = V1 / "visuals"
MET = V1 / "metrics"
VIS.mkdir(parents=True, exist_ok=True)
MET.mkdir(parents=True, exist_ok=True)

def load_mesh(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    obj = trimesh.load(path, process=False)
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

def sample_vertices(mesh, n=8000, seed=0):
    v = np.asarray(mesh.vertices)
    if len(v) <= n:
        return v
    rng = np.random.default_rng(seed)
    return v[rng.choice(len(v), n, replace=False)]

def distance_stats(a_mesh, b_mesh):
    a = sample_vertices(a_mesh, 8000, seed=1)
    b = sample_vertices(b_mesh, 8000, seed=2)
    tree = cKDTree(b)
    d, _ = tree.query(a, k=1)
    return {
        "min": float(d.min()),
        "p1": float(np.percentile(d, 1)),
        "p5": float(np.percentile(d, 5)),
        "p10": float(np.percentile(d, 10)),
        "mean": float(d.mean()),
        "within_02": int((d < 0.02).sum()),
        "within_05": int((d < 0.05).sum())
    }

def bbox_info(mesh):
    b = np.asarray(mesh.bounds)
    ext = b[1] - b[0]
    center = (b[0] + b[1]) / 2
    return {
        "center": center.tolist(),
        "extent": ext.tolist(),
        "diag": float(np.linalg.norm(ext))
    }

# IMPORTANT: use same-frame guidance hand and guidance object.
hand_path = SEL_RUN / "guidance_out/aket01_hand.ply"
obj_path = SEL_RUN / "guidance_out/aket01_obj.ply"

hand = load_mesh(hand_path)
obj = load_mesh(obj_path)

part_paths = sorted(ACTIVE.glob("*.ply"))
parts = [(p.stem, load_mesh(p)) for p in part_paths]

scene = trimesh.Scene()
scene.add_geometry(colorize(hand, [0, 255, 0, 150]), node_name="guidance_hand_green")
scene.add_geometry(colorize(obj, [255, 255, 255, 55]), node_name="guidance_object_white")

colors = {
    "body": [0, 180, 255, 155],
    "top_or_cap": [255, 0, 255, 155],
    "cap": [255, 0, 255, 155],
    "neck": [255, 180, 0, 180],
    "residual_uncertain": [255, 180, 0, 110],
}
for name, mesh in parts:
    scene.add_geometry(colorize(mesh, colors.get(name, [0, 0, 255, 120])), node_name=f"active_part_{name}")

out = VIS / "aket01_integrated_dryrun_v1_guidance_frame.glb"
scene.export(out)

# Union active parts for rough distance.
if parts:
    part_union = trimesh.util.concatenate([m for _, m in parts])
    hand_to_parts = distance_stats(hand, part_union)
    obj_to_parts = distance_stats(obj, part_union)
else:
    hand_to_parts = None
    obj_to_parts = None

report = {
    "case_id": "aket01",
    "stage": "dryrun_v1_guidance_frame",
    "decision": "VISUAL_REVIEW_REQUIRED",
    "hand_path": str(hand_path),
    "object_path": str(obj_path),
    "active_part_paths": [str(p) for p in part_paths],
    "visual": str(out),
    "bbox": {
        "hand": bbox_info(hand),
        "guidance_object": bbox_info(obj),
        "active_parts_union": bbox_info(part_union) if parts else None
    },
    "distances": {
        "hand_to_guidance_object": distance_stats(hand, obj),
        "hand_to_active_parts": hand_to_parts,
        "guidance_object_to_active_parts": obj_to_parts
    },
    "interpretation": [
        "This scene uses guidance_out hand and guidance_out object from the same source folder.",
        "If the hand is now near the bottle, v0 failure was caused by mixed coordinate families.",
        "If the hand still floats, run a root-frame provenance audit."
    ]
}

report_path = MET / "aket01_integrated_dryrun_v1_guidance_frame_report.json"
report_path.write_text(json.dumps(report, indent=2))

print("[OK] visual:", out)
print("[OK] report:", report_path)
print(json.dumps(report["distances"], indent=2))
