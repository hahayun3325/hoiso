from pathlib import Path
import json
import numpy as np
import trimesh

runs = {
    "selector_phase42": Path.home() / "foho_phase0/inspection/oakink_000/oakink000_gpt55_short_selector_phase42/internal_selector_debug",
    "selector_before42": Path.home() / "foho_phase0/inspection/oakink_000/oakink000_gpt55_short_selector_before42/internal_selector_debug",
}

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def score(path):
    mesh = load_mesh(path)
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0.0
    frag = (len(comps) - 1) + (1.0 - largest)
    bounds = mesh.bounds
    extent = bounds[1] - bounds[0]

    return {
        "path": str(path),
        "components": int(len(comps)),
        "largest_face_ratio": float(largest),
        "fragmentation_score": float(frag),
        "watertight": bool(mesh.is_watertight),
        "extent": [float(x) for x in extent],
    }

report = {}

for name, d in runs.items():
    candidates = sorted(d.glob("phase42_obj_transformed_before_joint_t4_opt0.ply"))
    if not candidates:
        candidates = sorted(d.glob("phase42_obj_transformed_before_joint*.ply"))

    if not candidates:
        report[name] = {"error": "missing candidate"}
        continue

    report[name] = score(candidates[0])

out = Path.home() / "foho_phase0/inspection/oakink_000/oakink000_gpt55_internal_selector_variant_scores.json"
out.write_text(json.dumps(report, indent=2))

print(json.dumps(report, indent=2))
print("[OK] wrote", out)
