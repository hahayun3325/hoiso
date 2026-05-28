from pathlib import Path
import json
import numpy as np
import trimesh

paths = {
    "hunyuan_initial_selected": Path.home() / "foho_phase0/inspection/object_source_selection/selected_object_source.ply",
    "smoke022_final_obj": Path.home() / "foho_phase0/runs/smoke_022_freeze_obj_pose_and_noise/guidance_out/test_obj.ply",
}

def score(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0
    frag = (len(comps) - 1) + (1 - largest)
    return {
        "path": str(path),
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "components": len(comps),
        "watertight": bool(mesh.is_watertight),
        "largest_face_ratio": float(largest),
        "fragmentation_score": float(frag),
    }

scores = {k: score(v) for k, v in paths.items()}
selected = min(scores, key=lambda k: scores[k]["fragmentation_score"])

report = {
    "selected": selected,
    "scores": scores,
    "interpretation": "Use the selected object for shape, then align/refine pose locally."
}

out = Path.home() / "foho_phase0/inspection/object_source_selection/fallback_selection_report.json"
out.write_text(json.dumps(report, indent=2))

print(json.dumps(report, indent=2))
print("[OK] wrote", out)
