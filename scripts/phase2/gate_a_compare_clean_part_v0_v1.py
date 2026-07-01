from pathlib import Path
import json
import trimesh
import numpy as np

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
V0 = CASE_ROOT / "integrated_gates/gate_a_part_repair/clean_parts_v0_largest_component"
V1 = CASE_ROOT / "integrated_gates/gate_a_part_repair/clean_parts_v1_component_merge"
OUT = CASE_ROOT / "integrated_gates/gate_a_part_repair"
rows = {}

for version, root in {"v0_largest": V0, "v1_merge": V1}.items():
    rows[version] = {}
    for part in ["screen", "keyboard_base", "hinge"]:
        p = root / f"{part}.ply"
        if not p.exists():
            rows[version][part] = {"exists": False}
            continue

        m = trimesh.load(p, force="mesh", process=False)
        comps = list(m.split(only_watertight=False))
        areas = [float(c.area) for c in comps]
        total_area = sum(areas) if areas else 0.0
        largest = max(areas) if areas else 0.0

        rows[version][part] = {
            "exists": True,
            "num_vertices": int(len(m.vertices)),
            "num_faces": int(len(m.faces)),
            "num_components": int(len(comps)),
            "area": float(m.area),
            "largest_component_area_ratio": float(largest / max(total_area, 1e-12)),
            "bbox_extent_xyz": np.asarray(m.bounds[1] - m.bounds[0]).tolist()
        }

out = OUT / "clean_parts_v0_vs_v1_compare.json"
out.write_text(json.dumps(rows, indent=2))

print("[OK] wrote", out)
print(json.dumps(rows, indent=2))
