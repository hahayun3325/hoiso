from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

DATA = Path("/home/fredcui/foho_phase0")
CASE = "alapuse02_v3b"
TOKEN = "alapuse02v3b"

case_root = DATA / "phase2_gateA_part_recon/cases" / CASE
run_root = DATA / "phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse02_v3b_selector_v41_refined_pipeline"

stage = case_root / "integrated_gates" / "shared_frame_dryrun_v1"
vis = stage / "visuals"
met = stage / "metrics"
notes = stage / "notes"
vis.mkdir(parents=True, exist_ok=True)
met.mkdir(parents=True, exist_ok=True)
notes.mkdir(parents=True, exist_ok=True)

hand_path = run_root / "guidance_out" / f"{TOKEN}_hand.ply"
obj_path = run_root / "guidance_out" / f"{TOKEN}_obj.ply"
aligned_mano_path = run_root / "aligned_mano" / f"{TOKEN}_hamer_aligned_mano.ply"
hunyuan_path = run_root / "hunyuan_hoi_out" / f"{TOKEN}_hoi_mesh.ply"

def load_mesh(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        geoms = [g for g in mesh.geometry.values() if hasattr(g, "vertices") and len(g.vertices) > 0]
        if not geoms:
            raise ValueError(f"empty scene: {path}")
        mesh = trimesh.util.concatenate(geoms)
    return mesh

def colorize(mesh, rgba):
    m = mesh.copy()
    m.visual.vertex_colors = rgba
    return m

def bbox_info(mesh):
    b = np.asarray(mesh.bounds)
    ext = b[1] - b[0]
    center = (b[0] + b[1]) / 2
    return {
        "center": center.tolist(),
        "extent": ext.tolist(),
        "diag": float(np.linalg.norm(ext)),
        "num_vertices": int(len(mesh.vertices)),
        "num_faces": int(len(mesh.faces)) if hasattr(mesh, "faces") else 0,
    }

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
        "within_01": int((d < 0.01).sum()),
        "within_02": int((d < 0.02).sum()),
        "within_05": int((d < 0.05).sum()),
    }

hand = load_mesh(hand_path)
obj = load_mesh(obj_path)

scene = trimesh.Scene()
scene.add_geometry(colorize(obj, [255, 255, 255, 80]), node_name="guidance_object_white")
scene.add_geometry(colorize(hand, [0, 255, 0, 160]), node_name="guidance_hand_green")

if aligned_mano_path.exists():
    aligned = load_mesh(aligned_mano_path)
    scene.add_geometry(colorize(aligned, [120, 120, 120, 70]), node_name="aligned_mano_gray_reference")
else:
    aligned = None

if hunyuan_path.exists():
    hunyuan = load_mesh(hunyuan_path)
    scene.add_geometry(colorize(hunyuan, [0, 160, 255, 45]), node_name="hunyuan_hoi_mesh_blue_reference")
else:
    hunyuan = None

glb_path = vis / "alapuse02_v3b_shared_frame_dryrun_v1.glb"
scene.export(glb_path)

# component count is useful for detecting one fused blob vs fragmented object
try:
    components = obj.split(only_watertight=False)
    component_sizes = sorted([len(c.vertices) for c in components], reverse=True)
except Exception as e:
    components = []
    component_sizes = []
    print("[WARN] component split failed:", e)

report = {
    "case": CASE,
    "stage": "shared_frame_dryrun_v1",
    "decision": "VISUAL_REVIEW_REQUIRED",
    "hand_path": str(hand_path),
    "object_path": str(obj_path),
    "visual": str(glb_path),
    "bbox": {
        "guidance_hand": bbox_info(hand),
        "guidance_object": bbox_info(obj),
        "aligned_mano_reference": bbox_info(aligned) if aligned is not None else None,
        "hunyuan_reference": bbox_info(hunyuan) if hunyuan is not None else None,
    },
    "object_components": {
        "num_components": int(len(component_sizes)),
        "largest_component_vertices": int(component_sizes[0]) if component_sizes else None,
        "top10_component_vertices": component_sizes[:10],
    },
    "distances": {
        "hand_to_guidance_object": distance_stats(hand, obj),
        "object_to_hand": distance_stats(obj, hand),
    },
    "decision_rule": {
        "PASS_SHARED_FRAME": "hand is visually near the laptop and contact/near-contact is plausible",
        "FAIL_FRAME_MISMATCH": "hand floats far away or is in a different coordinate family",
        "FAIL_OBJECT_UNUSABLE": "laptop object is a fused blob, collapsed, or visually not a laptop",
        "NEXT_IF_PASS": "run Gate A part reconstruction / part split for screen-base-hinge",
    },
}

report_path = met / "alapuse02_v3b_shared_frame_dryrun_v1_report.json"
report_path.write_text(json.dumps(report, indent=2))

decision_note = notes / "alapuse02_v3b_shared_frame_dryrun_v1_decision_template.md"
decision_note.write_text(f"""# alapuse02_v3b shared-frame dry-run v1 decision

## Files

- visual: `{glb_path}`
- report: `{report_path}`
- hand: `{hand_path}`
- object: `{obj_path}`

## Decision rule

If the green hand is near or touching the white laptop object:

`PASS_SHARED_FRAME`

If the green hand floats far from the laptop or appears in a different coordinate family:

`FAIL_FRAME_MISMATCH`

If the object is not recognizably a laptop or is too collapsed/fused for part splitting:

`FAIL_OBJECT_UNUSABLE`

## My decision

TODO after visual inspection.
""")

print("[OK] visual:", glb_path)
print("[OK] report:", report_path)
print(json.dumps(report["distances"], indent=2))
