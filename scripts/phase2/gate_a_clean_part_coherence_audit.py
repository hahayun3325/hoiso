from pathlib import Path
import json
import trimesh
import numpy as np

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
PART_DIR = CASE_ROOT / "integrated_gates/gate_a_part_repair/clean_parts_v0_largest_component"
OUT = CASE_ROOT / "integrated_gates/gate_a_part_repair/clean_parts_v0_largest_component"
rows = {}

for name in ["screen", "keyboard_base", "hinge"]:
    p = PART_DIR / f"{name}.ply"
    if not p.exists():
        rows[name] = {"exists": False}
        continue

    mesh = trimesh.load(p, force="mesh", process=False)
    comps = mesh.split(only_watertight=False)

    comp_areas = [float(c.area) for c in comps]
    total_area = sum(comp_areas) if comp_areas else 0.0
    largest_area = max(comp_areas) if comp_areas else 0.0
    largest_ratio = largest_area / max(total_area, 1e-12)

    rows[name] = {
        "exists": True,
        "num_vertices": int(len(mesh.vertices)),
        "num_faces": int(len(mesh.faces)),
        "num_components": int(len(comps)),
        "largest_component_area_ratio": largest_ratio,
        "bbox_extent_xyz": np.asarray(mesh.bounds[1] - mesh.bounds[0]).tolist(),
        "coherence_flag": "OK" if largest_ratio >= 0.90 and len(comps) == 1 else "STILL_NEEDS_REPAIR"
    }

out = OUT / "clean_parts_v0_coherence_audit.json"
out.write_text(json.dumps(rows, indent=2))

print("[OK] wrote", out)
for k, v in rows.items():
    print("\n==", k, "==")
    print(json.dumps(v, indent=2))
