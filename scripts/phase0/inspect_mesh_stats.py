from pathlib import Path
import trimesh

base = Path.home() / "foho_phase0/runs/smoke_013_octree192_guidance/guidance_out"

for name in ["test_obj.ply", "test_hand.ply"]:
    path = base / name

    print("\n================================================")
    print(name)
    print(path)

    if not path.exists():
        print("[MISSING]")
        continue

    mesh = trimesh.load(path, process=False)

    print("vertices:", len(mesh.vertices))
    print("faces:", len(mesh.faces))
    print("watertight:", mesh.is_watertight)
    print("bounds:", mesh.bounds)
    print("surface area:", mesh.area)

    try:
        print("volume:", mesh.volume)
    except Exception as e:
        print("volume failed:", repr(e))
