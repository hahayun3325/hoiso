from pathlib import Path
import trimesh

object_path = Path.home() / "foho_phase0/inspection/object_source_selection/selected_object_source.ply"
hand_path = Path.home() / "foho_phase0/runs/smoke_022_freeze_obj_pose_and_noise/guidance_out/test_hand.ply"

out_dir = Path.home() / "foho_phase0/inspection/object_source_selection"
out_dir.mkdir(parents=True, exist_ok=True)

obj = trimesh.load(object_path, process=False)
hand = trimesh.load(hand_path, process=False)

scene = trimesh.Scene()
scene.add_geometry(obj, geom_name="selected_object")
scene.add_geometry(hand, geom_name="final_hand")

out_glb = out_dir / "fallback_selected_object_plus_final_hand.glb"
out_png = out_dir / "fallback_selected_object_plus_final_hand.png"

scene.export(out_glb)
out_png.write_bytes(scene.save_image(resolution=(1400, 1000)))

print("[OK] wrote", out_glb)
print("[OK] wrote", out_png)
print("object bounds:", obj.bounds)
print("hand bounds:", hand.bounds)
