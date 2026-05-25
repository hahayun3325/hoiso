from pathlib import Path
import trimesh

base = Path.home() / "foho_phase0/runs/smoke_013_octree192_guidance/guidance_out"

for name in ["test_obj.ply", "test_hand.ply"]:
    path = base / name

    if not path.exists():
        print("[MISSING]", path)
        continue

    mesh = trimesh.load(path, process=False)

    scene = mesh.scene()
    png = scene.save_image(resolution=(1024, 1024))

    out = Path.home() / "foho_phase0/inspection" / f"{name}.png"
    out.write_bytes(png)

    print("[OK]", out)
