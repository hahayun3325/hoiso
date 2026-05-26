from pathlib import Path
import trimesh

cases = {
    "smoke013_final_obj": Path.home() / "foho_phase0/runs/smoke_013_octree192_guidance/guidance_out/test_obj.ply",
    "smoke015_hunyuan_hoi": Path.home() / "foho_phase0/runs/smoke_015_prompt_rect/hunyuan_hoi_out/test_hoi_mesh.ply",
}

out_dir = Path.home() / "foho_phase0/inspection/prompt_ablation"
out_dir.mkdir(parents=True, exist_ok=True)

for name, path in cases.items():
    print("\n=====", name, "=====")
    print(path)

    if not path.exists():
        print("[MISSING]")
        continue

    mesh = trimesh.load(path, process=False)
    print("type:", type(mesh))

    if isinstance(mesh, trimesh.Scene):
        print("geometry count:", len(mesh.geometry))
        scene = mesh
    else:
        print("vertices:", len(mesh.vertices))
        print("faces:", len(mesh.faces))
        print("bounds:", mesh.bounds)
        print("watertight:", getattr(mesh, "is_watertight", "NA"))
        scene = mesh.scene()

    png = scene.save_image(resolution=(1024, 1024))
    out = out_dir / f"{name}.png"
    out.write_bytes(png)
    print("[OK]", out)
