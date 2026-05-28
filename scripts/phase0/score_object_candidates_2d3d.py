from pathlib import Path
import json
import numpy as np
import trimesh

candidates = {
    "hunyuan_initial": Path.home() / "foho_phase0/runs/smoke_015_prompt_rect/hunyuan_hoi_out/test_hoi_mesh.ply",
    "smoke022_final_obj": Path.home() / "foho_phase0/runs/smoke_022_freeze_obj_pose_and_noise/guidance_out/test_obj.ply",
}

def mesh_score(path: Path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    comps = mesh.split(only_watertight=False)
    comp_faces = np.array([len(c.faces) for c in comps], dtype=np.float64)

    largest_ratio = comp_faces.max() / max(len(mesh.faces), 1) if len(comp_faces) else 0.0
    fragmentation_score = (len(comps) - 1) + (1.0 - largest_ratio)

    return {
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "components": len(comps),
        "watertight": bool(mesh.is_watertight),
        "largest_face_ratio": float(largest_ratio),
        "fragmentation_score": float(fragmentation_score),
        "bounds_min": mesh.bounds[0].tolist(),
        "bounds_max": mesh.bounds[1].tolist(),
    }

scores = {name: mesh_score(path) for name, path in candidates.items()}

# Lower score is better. Later add 2D silhouette IoU and MoGe point-cloud distance.
selected = min(scores.keys(), key=lambda k: scores[k]["fragmentation_score"])

report = {
    "selected_by_3d_completeness": selected,
    "scores": scores,
    "next_metrics_to_add": [
        "2D silhouette IoU",
        "MoGe partial point cloud distance",
        "contact distance",
        "penetration volume"
    ],
}

out = Path.home() / "foho_phase0/inspection/object_source_selection/object_candidate_2d3d_score.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2))

print(json.dumps(report, indent=2))
print("[OK] wrote", out)
