from pathlib import Path
import numpy as np
import trimesh

selected_path = Path.home() / "foho_phase0/inspection/object_source_selection/selected_object_source.ply"
target_path = Path.home() / "foho_phase0/runs/smoke_022_freeze_obj_pose_and_noise/guidance_out/test_obj.ply"
hand_path = Path.home() / "foho_phase0/runs/smoke_022_freeze_obj_pose_and_noise/guidance_out/test_hand.ply"

out_dir = Path.home() / "foho_phase0/inspection/object_source_selection"
out_dir.mkdir(parents=True, exist_ok=True)

selected = trimesh.load(selected_path, process=False)
target = trimesh.load(target_path, process=False)
hand = trimesh.load(hand_path, process=False)

def center_and_extent(mesh):
    bounds = mesh.bounds
    center = bounds.mean(axis=0)
    extent = bounds[1] - bounds[0]
    return center, extent

src_center, src_extent = center_and_extent(selected)
tgt_center, tgt_extent = center_and_extent(target)

scale = np.linalg.norm(tgt_extent) / max(np.linalg.norm(src_extent), 1e-8)

aligned = selected.copy()
aligned.vertices = (aligned.vertices - src_center) * scale + tgt_center

aligned_path = out_dir / "selected_object_bbox_aligned_to_final_obj.ply"
aligned.export(aligned_path)

scene = trimesh.Scene()
scene.add_geometry(aligned, geom_name="bbox_aligned_selected_object")
scene.add_geometry(hand, geom_name="final_hand")

scene_path = out_dir / "bbox_aligned_selected_object_plus_final_hand.glb"
png_path = out_dir / "bbox_aligned_selected_object_plus_final_hand.png"

scene.export(scene_path)
png_path.write_bytes(scene.save_image(resolution=(1400, 1000)))

print("[OK] wrote", aligned_path)
print("[OK] wrote", scene_path)
print("[OK] wrote", png_path)
print("src_center:", src_center)
print("tgt_center:", tgt_center)
print("scale:", scale)
