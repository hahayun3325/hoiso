from pathlib import Path
import json
import trimesh
import numpy as np

CASE_ROOT = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01")
PART_DIR = CASE_ROOT / "part_meshes_partfield_v2_vmap"
OUT = CASE_ROOT / "gate_d0_object_repair/next_integrated_image_evidence_fit/metrics"
OUT.mkdir(parents=True, exist_ok=True)

rows = {}

for name in ["screen", "keyboard_base", "hinge", "residual_uncertain"]:
    p = PART_DIR / f"{name}.ply"
    if not p.exists():
        rows[name] = {"exists": False}
        continue

    mesh = trimesh.load(p, force="mesh", process=False)
    comps = mesh.split(only_watertight=False)

    comp_faces = [len(c.faces) for c in comps]
    comp_vertices = [len(c.vertices) for c in comps]
    comp_areas = [float(c.area) for c in comps]

    total_area = sum(comp_areas) if comp_areas else 0.0
    largest_area = max(comp_areas) if comp_areas else 0.0
    largest_ratio = largest_area / max(total_area, 1e-12)

    extent = np.asarray(mesh.bounds[1] - mesh.bounds[0]).tolist()

    rows[name] = {
        "exists": True,
        "num_vertices": int(len(mesh.vertices)),
        "num_faces": int(len(mesh.faces)),
        "num_components": int(len(comps)),
        "largest_component_area_ratio": largest_ratio,
        "bbox_extent_xyz": extent,
        "component_faces_top10": sorted(comp_faces, reverse=True)[:10],
        "component_vertices_top10": sorted(comp_vertices, reverse=True)[:10],
        "coherence_flag": "OK" if largest_ratio >= 0.70 and len(comps) <= 20 else "FRAGMENTED_OR_NOISY"
    }

out = OUT / "alapuse01_gate_a_part_coherence_audit.json"
out.write_text(json.dumps(rows, indent=2))

print("[OK] wrote", out)
for k, v in rows.items():
    print("\n==", k, "==")
    print(json.dumps(v, indent=2)[:1200])
