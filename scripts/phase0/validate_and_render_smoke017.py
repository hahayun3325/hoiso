from pathlib import Path
import trimesh

base = Path.home() / "foho_phase0/runs/smoke_017_prompt_rect_guidance_octree192_steps6/guidance_out"
out_dir = Path.home() / "foho_phase0/inspection/prompt_ablation"
out_dir.mkdir(parents=True, exist_ok=True)

paths = {
    "smoke017_final_obj": base / "test_obj.ply",
    "smoke017_final_hand": base / "test_hand.ply",
}

ok = True

for name, path in paths.items():
    print(f"\n===== {name} =====")
    print(path)

    if not path.exists():
        print("[MISSING]")
        ok = False
        continue

    mesh = trimesh.load(path, process=False)
    print("type:", type(mesh))
    print("vertices:", len(mesh.vertices))
    print("faces:", len(mesh.faces))
    print("bounds:", mesh.bounds)
    print("watertight:", mesh.is_watertight)

    if len(mesh.vertices) == 0:
        ok = False
        print("[BAD] empty mesh")
        continue

    png = mesh.scene().save_image(resolution=(1024, 1024))
    out = out_dir / f"{name}.png"
    out.write_bytes(png)
    print("[OK] rendered", out)

raise SystemExit(0 if ok else 1)
