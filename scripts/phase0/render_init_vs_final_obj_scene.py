from pathlib import Path
import trimesh

out_dir = Path.home() / "foho_phase0/inspection/prompt_ablation"
out_dir.mkdir(parents=True, exist_ok=True)

init_path = Path.home() / "foho_phase0/runs/smoke_015_prompt_rect/hunyuan_hoi_out/test_hoi_mesh.ply"
final_path = Path.home() / "foho_phase0/runs/smoke_017_prompt_rect_guidance_octree192_steps6/guidance_out/test_obj.ply"

init_mesh = trimesh.load(init_path, process=False)
final_mesh = trimesh.load(final_path, process=False)

scene = trimesh.Scene()
scene.add_geometry(init_mesh, geom_name="smoke015_hunyuan_initial")
scene.add_geometry(final_mesh, geom_name="smoke017_final_object")

out = out_dir / "smoke015_init_vs_smoke017_final_scene.glb"
scene.export(out)

png = scene.save_image(resolution=(1400, 1000))
out_png = out_dir / "smoke015_init_vs_smoke017_final_scene.png"
out_png.write_bytes(png)

print("[OK] wrote", out)
print("[OK] wrote", out_png)
print("init bounds:", init_mesh.bounds)
print("final bounds:", final_mesh.bounds)
