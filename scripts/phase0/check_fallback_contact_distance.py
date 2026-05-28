from pathlib import Path
import trimesh
import numpy as np
from scipy.spatial import cKDTree

cases = {
    "raw_selected_plus_final_hand": (
        Path.home() / "foho_phase0/inspection/object_source_selection/selected_object_source.ply",
        Path.home() / "foho_phase0/runs/smoke_022_freeze_obj_pose_and_noise/guidance_out/test_hand.ply",
    ),
    "bbox_aligned_selected_plus_final_hand": (
        Path.home() / "foho_phase0/inspection/object_source_selection/selected_object_bbox_aligned_to_final_obj.ply",
        Path.home() / "foho_phase0/runs/smoke_022_freeze_obj_pose_and_noise/guidance_out/test_hand.ply",
    ),
}

print("case,mean_hand_to_obj_dist,min_hand_to_obj_dist,p05_hand_to_obj_dist")

for name, (obj_path, hand_path) in cases.items():
    obj = trimesh.load(obj_path, process=False)
    hand = trimesh.load(hand_path, process=False)

    obj_pts, _ = trimesh.sample.sample_surface(obj, 30000)
    hand_pts, _ = trimesh.sample.sample_surface(hand, 5000)

    tree = cKDTree(obj_pts)
    dists, _ = tree.query(hand_pts, k=1)

    print(
        f"{name},"
        f"{float(np.mean(dists)):.6f},"
        f"{float(np.min(dists)):.6f},"
        f"{float(np.percentile(dists, 5)):.6f}"
    )
