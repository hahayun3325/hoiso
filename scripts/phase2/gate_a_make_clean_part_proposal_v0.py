from pathlib import Path
import json
import trimesh

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
PART_DIR = CASE_ROOT / "part_meshes_partfield_v2_vmap"
OUT_DIR = CASE_ROOT / "integrated_gates/gate_a_part_repair/clean_parts_v0_largest_component"
OUT_DIR.mkdir(parents=True, exist_ok=True)

report = {}

for part_name in ["screen", "keyboard_base", "hinge"]:
    path = PART_DIR / f"{part_name}.ply"
    if not path.exists():
        report[part_name] = {"exists": False}
        continue

    mesh = trimesh.load(path, force="mesh", process=False)
    comps = list(mesh.split(only_watertight=False))

    if not comps:
        report[part_name] = {"exists": True, "error": "no components"}
        continue

    comps_sorted = sorted(comps, key=lambda c: c.area, reverse=True)
    chosen = comps_sorted[0]

    out_path = OUT_DIR / f"{part_name}.ply"
    chosen.export(out_path)

    total_area = sum(float(c.area) for c in comps_sorted)
    report[part_name] = {
        "exists": True,
        "source": str(path),
        "output": str(out_path),
        "num_components_before": len(comps_sorted),
        "chosen_component_area": float(chosen.area),
        "total_area_before": total_area,
        "chosen_area_ratio": float(chosen.area / max(total_area, 1e-12)),
        "num_vertices": int(len(chosen.vertices)),
        "num_faces": int(len(chosen.faces)),
        "bbox_extent": (chosen.bounds[1] - chosen.bounds[0]).tolist()
    }

# Create a combined scene.
scene = trimesh.Scene()
colors = {
    "screen": [0, 0, 255, 180],
    "keyboard_base": [255, 140, 0, 200],
    "hinge": [255, 0, 255, 220],
}
for part_name, rgba in colors.items():
    p = OUT_DIR / f"{part_name}.ply"
    if p.exists():
        m = trimesh.load(p, force="mesh", process=False)
        m.visual.vertex_colors = rgba
        scene.add_geometry(m, node_name=part_name)

scene_path = OUT_DIR / "clean_parts_v0_scene.glb"
scene.export(scene_path)

out_json = OUT_DIR / "clean_parts_v0_report.json"
out_json.write_text(json.dumps(report, indent=2))

print("[OK] wrote", out_json)
print("[OK] wrote", scene_path)
print(json.dumps(report, indent=2))
