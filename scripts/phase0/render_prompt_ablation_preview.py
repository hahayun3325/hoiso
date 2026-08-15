from pathlib import Path
import trimesh

cases = {
    "baseline_smoke_013": Path.home() / "foho_phase0/runs/smoke_013_octree192_guidance/guidance_out/test_obj.ply",
    "prompt_rect_smoke_015": Path.home() / "foho_phase0/runs/smoke_015_prompt_rect/guidance_out/test_obj.ply",
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
    print("vertices:", len(mesh.vertices))
    print("faces:", len(mesh.faces))
    print("bounds:", mesh.bounds)
    print("watertight:", mesh.is_watertight)

    png = mesh.scene().save_image(resolution=(1024, 1024))
    out = out_dir / f"{name}.png"
    out.write_bytes(png)
    print("[OK]", out)
