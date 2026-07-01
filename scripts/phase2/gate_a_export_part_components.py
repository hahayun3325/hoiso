from pathlib import Path
import json
import trimesh

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
PART_DIR = CASE_ROOT / "part_meshes_partfield_v2_vmap"
OUT_DIR = CASE_ROOT / "integrated_gates/gate_a_part_repair/components"
OUT_DIR.mkdir(parents=True, exist_ok=True)

summary = {}

for part_name in ["screen", "keyboard_base", "hinge", "residual_uncertain"]:
    path = PART_DIR / f"{part_name}.ply"
    if not path.exists():
        summary[part_name] = {"exists": False}
        continue

    mesh = trimesh.load(path, force="mesh", process=False)
    comps = mesh.split(only_watertight=False)

    rows = []
    for i, comp in enumerate(comps):
        comp_path = OUT_DIR / f"{part_name}_component_{i:02d}.ply"
        comp.export(comp_path)
        rows.append({
            "component_id": i,
            "path": str(comp_path),
            "num_vertices": int(len(comp.vertices)),
            "num_faces": int(len(comp.faces)),
            "area": float(comp.area),
            "bbox_extent": (comp.bounds[1] - comp.bounds[0]).tolist()
        })

    rows = sorted(rows, key=lambda x: x["area"], reverse=True)
    summary[part_name] = {
        "exists": True,
        "num_components": len(comps),
        "components_sorted_by_area": rows
    }

out_json = OUT_DIR / "component_summary.json"
out_json.write_text(json.dumps(summary, indent=2))

print("[OK] wrote", out_json)
for k, v in summary.items():
    print("\n==", k, "==")
    print(json.dumps(v, indent=2)[:1600])
