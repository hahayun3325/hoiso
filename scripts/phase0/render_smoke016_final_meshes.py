from pathlib import Path
import trimesh

cases = {
    "smoke016_final_obj": Path.home() / "foho_phase0/runs/smoke_016_prompt_rect_guidance_ultralow/guidance_out/test_obj.ply",
    "smoke016_final_hand": Path.home() / "foho_phase0/runs/smoke_016_prompt_rect_guidance_ultralow/guidance_out/test_hand.ply",
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
