from pathlib import Path
import argparse
import json
import numpy as np
import trimesh

ap = argparse.ArgumentParser()
ap.add_argument("--debug_dir", required=True)
args = ap.parse_args()

debug_dir = Path(args.debug_dir).expanduser()
out_json = debug_dir / "internal_selector_debug_scores.json"

def score(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0.0
    frag = (len(comps) - 1) + (1.0 - largest)
    return {
        "path": str(path),
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "components": len(comps),
        "largest_face_ratio": float(largest),
        "fragmentation_score": float(frag),
        "watertight": bool(mesh.is_watertight),
    }

scores = {}
for p in sorted(debug_dir.glob("*.ply")):
    scores[p.name] = score(p)

out_json.write_text(json.dumps(scores, indent=2))
print("[OK] wrote", out_json)

for k, v in scores.items():
    print(k, "comp=", v["components"], "frag=", round(v["fragmentation_score"], 4))
