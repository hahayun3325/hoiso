from pathlib import Path
import numpy as np
import trimesh
import hashlib
import json

p_current = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01/input/final_object_singleblob.ply")
p_v41 = Path("/home/fredcui/foho_phase0/phase1_report_assets/meshes/alapuse01/selector_v41/final_object.ply")

def load_mesh(p):
    return trimesh.load(p, force="mesh", process=False)

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

m0 = load_mesh(p_current)
m1 = load_mesh(p_v41)

same_counts = len(m0.vertices) == len(m1.vertices) and len(m0.faces) == len(m1.faces)
same_bounds = np.allclose(m0.bounds, m1.bounds)
same_vertices = same_counts and np.allclose(np.asarray(m0.vertices), np.asarray(m1.vertices))
same_faces = same_counts and np.array_equal(np.asarray(m0.faces), np.asarray(m1.faces))

report = {
    "current": str(p_current),
    "selector_v41": str(p_v41),
    "current_sha256": sha256_file(p_current),
    "selector_v41_sha256": sha256_file(p_v41),
    "same_counts": bool(same_counts),
    "same_bounds": bool(same_bounds),
    "same_vertices": bool(same_vertices),
    "same_faces": bool(same_faces),
    "current_vertices": int(len(m0.vertices)),
    "selector_v41_vertices": int(len(m1.vertices)),
    "current_faces": int(len(m0.faces)),
    "selector_v41_faces": int(len(m1.faces)),
    "decision": "same_object_seed" if same_vertices and same_faces else "not_identical_but_maybe_same_geometry"
}

out = Path("/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse01/gt_reference/current_equals_selector_v41_check.json")
out.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
print("[OK] wrote", out)
