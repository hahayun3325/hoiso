from pathlib import Path
import trimesh

base = Path.home() / "foho_phase0/runs/smoke_017_prompt_rect_guidance_octree192_steps6/guidance_out"
out_dir = Path.home() / "foho_phase0/inspection/prompt_ablation"
out_dir.mkdir(parents=True, exist_ok=True)

obj_path = base / "test_obj.ply"
hand_path = base / "test_hand.ply"

obj = trimesh.load(obj_path, process=False)
hand = trimesh.load(hand_path, process=False)

scene = trimesh.Scene()
scene.add_geometry(obj, geom_name="object")
scene.add_geometry(hand, geom_name="hand")

out_glb = out_dir / "smoke017_final_hoi_scene.glb"
scene.export(out_glb)

png = scene.save_image(resolution=(1400, 1000))
out_png = out_dir / "smoke017_final_hoi_scene.png"
out_png.write_bytes(png)

print("[OK] wrote", out_glb)
print("[OK] wrote", out_png)
print("object bounds:", obj.bounds)
print("hand bounds:", hand.bounds)
