from pathlib import Path
import json
import trimesh
import numpy as np
from scipy.spatial import cKDTree

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT_ROOT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit"
MANIFEST = FIT_ROOT / "metrics/standalone_fitter_input_manifest.json"

OUT_VIS = FIT_ROOT / "visuals"
OUT_METRICS = FIT_ROOT / "metrics"
OUT_VIS.mkdir(parents=True, exist_ok=True)
OUT_METRICS.mkdir(parents=True, exist_ok=True)

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

def mesh_stats(mesh):
    comps = mesh.split(only_watertight=False)
    areas = [float(c.area) for c in comps]
    total_area = sum(areas) if areas else 0.0
    largest = max(areas) if areas else 0.0
    return {
        "num_vertices": int(len(mesh.vertices)),
        "num_faces": int(len(mesh.faces)),
        "num_components": int(len(comps)),
        "area": float(mesh.area),
        "largest_component_area_ratio": float(largest / max(total_area, 1e-12)),
        "bbox_extent_xyz": np.asarray(mesh.bounds[1] - mesh.bounds[0]).tolist(),
    }

def sample(mesh, n=6000, seed=0):
    rng = np.random.default_rng(seed)
    if len(mesh.faces) > 0:
        pts, _ = trimesh.sample.sample_surface(mesh, min(n, max(n, len(mesh.faces))))
        return pts
    v = np.asarray(mesh.vertices)
    if len(v) <= n:
        return v
    return v[rng.choice(len(v), size=n, replace=False)]

data = json.loads(MANIFEST.read_text())
paths = {k: Path(v["path"]) for k, v in data["paths"].items() if v["exists"]}

screen = load_mesh(paths["screen_part"])
base = load_mesh(paths["keyboard_base_part"])
hinge = load_mesh(paths["hinge_part"])

stats = {
    "screen": mesh_stats(screen),
    "keyboard_base": mesh_stats(base),
    "hinge": mesh_stats(hinge),
}

# Simple hinge proximity diagnostic.
s_pts = sample(screen, 8000, seed=1)
b_pts = sample(base, 8000, seed=2)
d_sb, _ = cKDTree(b_pts).query(s_pts, k=1)
stats["screen_to_base_distance"] = {
    "min": float(d_sb.min()),
    "p1": float(np.percentile(d_sb, 1)),
    "p5": float(np.percentile(d_sb, 5)),
    "mean": float(d_sb.mean()),
}

scene = trimesh.Scene()
scene.add_geometry(colorize(screen, [0, 0, 255, 160]), node_name="active_screen_blue")
scene.add_geometry(colorize(base, [255, 140, 0, 200]), node_name="active_keyboard_base_orange")
scene.add_geometry(colorize(hinge, [255, 0, 255, 220]), node_name="active_hinge_magenta")

if "guidance_obj" in paths:
    scene.add_geometry(colorize(load_mesh(paths["guidance_obj"]), [180, 180, 180, 70]), node_name="current_guidance_obj_gray")

if "guidance_hand" in paths:
    scene.add_geometry(colorize(load_mesh(paths["guidance_hand"]), [0, 255, 0, 120]), node_name="current_guidance_hand_green")

out_glb = OUT_VIS / "standalone_fitter_v0_input_dryrun_scene.glb"
out_json = OUT_METRICS / "standalone_fitter_v0_input_dryrun_stats.json"

scene.export(out_glb)
out_json.write_text(json.dumps(stats, indent=2))

print("[OK] wrote", out_glb)
print("[OK] wrote", out_json)
print(json.dumps(stats, indent=2))
