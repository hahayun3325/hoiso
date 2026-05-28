from pathlib import Path
import json
import shutil
import numpy as np
import trimesh

candidates = {
    "hunyuan_initial": Path.home() / "foho_phase0/runs/smoke_015_prompt_rect/hunyuan_hoi_out/test_hoi_mesh.ply",
    "smoke021_final_obj": Path.home() / "foho_phase0/runs/smoke_021_verified_freeze_obj_noise/guidance_out/test_obj.ply",
}

out_dir = Path.home() / "foho_phase0/inspection/object_source_selection"
out_dir.mkdir(parents=True, exist_ok=True)

def score_mesh(path: Path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    comps = mesh.split(only_watertight=False)
    comp_faces = np.array([len(c.faces) for c in comps], dtype=np.float64)

    largest_ratio = comp_faces.max() / max(len(mesh.faces), 1) if len(comp_faces) else 0.0
    fragmentation_score = (len(comps) - 1) + (1.0 - largest_ratio)

    return {
        "path": str(path),
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "components": len(comps),
        "watertight": bool(mesh.is_watertight),
        "largest_face_ratio": float(largest_ratio),
        "fragmentation_score": float(fragmentation_score),
    }

scores = {name: score_mesh(path) for name, path in candidates.items()}

# Lower fragmentation score is better.
selected_name = min(scores.keys(), key=lambda k: scores[k]["fragmentation_score"])
selected_path = Path(scores[selected_name]["path"])

out_mesh = out_dir / "selected_object_source.ply"
shutil.copy2(selected_path, out_mesh)

report = {
    "selected": selected_name,
    "selected_path": str(selected_path),
    "output_mesh": str(out_mesh),
    "scores": scores,
}

report_path = out_dir / "object_source_selection_report.json"
report_path.write_text(json.dumps(report, indent=2))

print(json.dumps(report, indent=2))
print("[OK] copied selected mesh to", out_mesh)
