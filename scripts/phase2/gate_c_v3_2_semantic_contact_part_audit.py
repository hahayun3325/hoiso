from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
FIT_ROOT = CASE_ROOT / "integrated_gates/gate_d0_image_evidence_fit"
MANIFEST = FIT_ROOT / "metrics/standalone_fitter_input_manifest.json"
ACTIVE = CASE_ROOT / "integrated_gates/gate_a_part_repair/active_clean_parts"

CONTACT_TARGET = CASE_ROOT / "integrated_gates/gate_d_contact_scorer_v0/outputs/verified_contact_patch_target_v0.json"

OUT = CASE_ROOT / "integrated_gates/gate_c_v3_2_semantic_part_audit"
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
    tree = cKDTree(verts)
    d, idx = tree.query(points, k=1)
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

def mesh_info(mesh):
    comps = list(mesh.split(only_watertight=False))
    areas = [float(c.area) for c in comps]
    return {
        "num_vertices": int(len(mesh.vertices)),
        "num_faces": int(len(mesh.faces)),
        "num_components": int(len(comps)),
        "area": float(mesh.area),
        "bbox_min": np.asarray(mesh.bounds[0]).tolist(),
        "bbox_max": np.asarray(mesh.bounds[1]).tolist(),
        "bbox_extent": np.asarray(mesh.bounds[1] - mesh.bounds[0]).tolist(),
        "component_areas": areas
    }

data = json.loads(MANIFEST.read_text())
paths = {k: Path(v["path"]) for k, v in data["paths"].items() if v["exists"]}

target = json.loads(CONTACT_TARGET.read_text())
patch_hand_pts = np.asarray(target["hand_patch_points"], dtype=float)

screen = load_mesh(ACTIVE / "screen.ply")
base = load_mesh(ACTIVE / "keyboard_base.ply")
hinge = load_mesh(ACTIVE / "hinge.ply")
hand = load_mesh(paths["guidance_hand"])

# Split screen into components to see which sub-component the patch really touches.
screen_components = list(screen.split(only_watertight=False))
screen_components = sorted(screen_components, key=lambda m: m.area, reverse=True)

part_meshes = {
    "screen_all": screen,
    "keyboard_base": base,
    "hinge": hinge
}
for i, comp in enumerate(screen_components):
    part_meshes[f"screen_component_{i:02d}_sorted_by_area"] = comp

part_scores = {}
for name, mesh in part_meshes.items():
    part_scores[name] = {
        "mesh_info": mesh_info(mesh),
        "patch_to_part_distance": dist_stats(patch_hand_pts, mesh)
    }

# Rank by patch mean distance.
ranking = sorted(
    [
        {
            "part": name,
            "mean": info["patch_to_part_distance"]["mean"],
            "p5": info["patch_to_part_distance"]["p5"],
            "within_10mm": info["patch_to_part_distance"]["within_10mm"],
            "within_20mm": info["patch_to_part_distance"]["within_20mm"]
        }
        for name, info in part_scores.items()
    ],
    key=lambda x: (x["mean"], -x["within_10mm"])
)

result = {
    "case_id": "alapuse01",
    "stage": "Gate C v3.2 semantic contact-part audit",
    "purpose": "check whether the verified contact patch touches desired screen/top-lid or base-like geometry",
    "input_contact_target": str(CONTACT_TARGET),
    "patch_num_points": int(len(patch_hand_pts)),
    "part_scores": part_scores,
    "ranking_by_patch_distance": ranking,
    "preliminary_decision": "VISUAL_CHECK_REQUIRED",
    "decision_rule": {
        "pass": "patch is closest to the visually desired top-lid/screen component",
        "semantic_fail": "patch is closest to keyboard_base or a base-like screen subcomponent",
        "repair_needed": "screen components are semantically mixed and require Gate A v2 mask-guided repair"
    }
}

out_json = OUT_METRICS / "gate_c_v3_2_semantic_contact_part_audit.json"
out_json.write_text(json.dumps(result, indent=2))

scene = trimesh.Scene()
scene.add_geometry(colorize(hand, [0, 255, 0, 80]), node_name="guidance_hand_green")
scene.add_geometry(colorize(base, [255, 140, 0, 160]), node_name="keyboard_base_orange")
scene.add_geometry(colorize(hinge, [255, 0, 255, 220]), node_name="hinge_magenta")

colors = [
    [0, 0, 255, 140],
    [0, 255, 255, 140],
    [120, 120, 255, 140],
    [50, 50, 180, 140]
]
for i, comp in enumerate(screen_components):
    rgba = colors[i % len(colors)]
    scene.add_geometry(colorize(comp, rgba), node_name=f"screen_component_{i:02d}")

for i, p in enumerate(patch_hand_pts):
    scene.add_geometry(marker(p, 0.004, [255, 0, 0, 255]), node_name=f"hand_patch_red_{i:03d}")

out_glb = OUT_VIS / "gate_c_v3_2_semantic_contact_part_audit.glb"
scene.export(out_glb)

print("[OK] wrote", out_json)
print("[OK] wrote", out_glb)
print("[ranking]")
for r in ranking:
    print(r)
