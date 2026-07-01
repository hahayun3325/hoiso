from pathlib import Path
import json
import trimesh
import numpy as np

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
COMP_DIR = CASE_ROOT / "integrated_gates/gate_a_part_repair/components"
OUT_DIR = CASE_ROOT / "integrated_gates/gate_a_part_repair/clean_parts_v1_component_merge"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Based on visual inspection:
# screen_component_01 and screen_component_02 are pad-like pieces.
# screen_component_00 is a thin line, so drop it.
selection = {
    "screen": [
        COMP_DIR / "screen_component_01.ply",
        COMP_DIR / "screen_component_02.ply",
    ],
    "keyboard_base": [
        COMP_DIR / "keyboard_base_component_00.ply",
    ],
    "hinge": [
        COMP_DIR / "hinge_component_00.ply",
    ],
}

colors = {
    "screen": [0, 0, 255, 180],
    "keyboard_base": [255, 140, 0, 200],
    "hinge": [255, 0, 255, 220],
}

report = {}
scene = trimesh.Scene()

for part_name, paths in selection.items():
    meshes = []
    missing = []

    for p in paths:
        if not p.exists():
            missing.append(str(p))
            continue
        meshes.append(trimesh.load(p, force="mesh", process=False))

    if missing:
        report[part_name] = {"exists": False, "missing": missing}
        continue

    merged = trimesh.util.concatenate(meshes)
    out_path = OUT_DIR / f"{part_name}.ply"
    merged.export(out_path)

    comps = list(merged.split(only_watertight=False))
    comp_areas = [float(c.area) for c in comps]
    total_area = sum(comp_areas) if comp_areas else 0.0
    largest_area = max(comp_areas) if comp_areas else 0.0

    report[part_name] = {
        "exists": True,
        "selected_components": [str(p) for p in paths],
        "output": str(out_path),
        "num_vertices": int(len(merged.vertices)),
        "num_faces": int(len(merged.faces)),
        "num_components_after_merge": int(len(comps)),
        "largest_component_area_ratio_after_merge": float(largest_area / max(total_area, 1e-12)),
        "bbox_extent_xyz": np.asarray(merged.bounds[1] - merged.bounds[0]).tolist(),
        "note": "Multiple components can be acceptable if visual inspection shows they belong to the same physical part."
    }

    vis = merged.copy()
    vis.visual.vertex_colors = colors[part_name]
    scene.add_geometry(vis, node_name=part_name)

scene_path = OUT_DIR / "clean_parts_v1_component_merge_scene.glb"
scene.export(scene_path)

out_json = OUT_DIR / "clean_parts_v1_component_merge_report.json"
out_json.write_text(json.dumps(report, indent=2))

print("[OK] wrote", out_json)
print("[OK] wrote", scene_path)
print(json.dumps(report, indent=2))
