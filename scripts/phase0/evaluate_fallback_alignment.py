from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree

cases = {
    "raw_selected_plus_final_hand": {
        "obj": Path.home() / "foho_phase0/inspection/object_source_selection/selected_object_source.ply",
        "hand": Path.home() / "foho_phase0/runs/smoke_022_freeze_obj_pose_and_noise/guidance_out/test_hand.ply",
    },
    "bbox_aligned_selected_plus_final_hand": {
        "obj": Path.home() / "foho_phase0/inspection/object_source_selection/selected_object_bbox_aligned_to_final_obj.ply",
        "hand": Path.home() / "foho_phase0/runs/smoke_022_freeze_obj_pose_and_noise/guidance_out/test_hand.ply",
    },
}

def bbox_info(mesh):
    b = mesh.bounds
    center = b.mean(axis=0)
    extent = b[1] - b[0]
    return center, extent

def hand_to_obj_distance(obj, hand):
    obj_pts, _ = trimesh.sample.sample_surface(obj, 30000)
    hand_pts, _ = trimesh.sample.sample_surface(hand, 5000)
    tree = cKDTree(obj_pts)
    d, _ = tree.query(hand_pts, k=1)
    return {
        "mean": float(np.mean(d)),
        "min": float(np.min(d)),
        "p05": float(np.percentile(d, 5)),
        "p50": float(np.percentile(d, 50)),
    }

report = {}

for name, paths in cases.items():
    obj = trimesh.load(paths["obj"], process=False)
    hand = trimesh.load(paths["hand"], process=False)

    obj_center, obj_extent = bbox_info(obj)
    hand_center, hand_extent = bbox_info(hand)

    report[name] = {
        "object_path": str(paths["obj"]),
        "hand_path": str(paths["hand"]),
        "object_center": obj_center.tolist(),
        "hand_center": hand_center.tolist(),
        "center_distance": float(np.linalg.norm(obj_center - hand_center)),
        "object_extent": obj_extent.tolist(),
        "hand_extent": hand_extent.tolist(),
        "hand_to_object_distance": hand_to_obj_distance(obj, hand),
    }

out = Path.home() / "foho_phase0/inspection/object_source_selection/fallback_alignment_eval.json"
out.write_text(json.dumps(report, indent=2))

print(json.dumps(report, indent=2))
print("[OK] wrote", out)
