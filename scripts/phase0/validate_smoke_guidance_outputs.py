from pathlib import Path
import trimesh

base = Path.home() / "foho_phase0/runs/smoke_013_octree192_guidance"
paths = {
    "object": base / "guidance_out/test_obj.ply",
    "hand": base / "guidance_out/test_hand.ply",
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
    vertices = len(mesh.vertices) if hasattr(mesh, "vertices") else 0
    faces = len(mesh.faces) if hasattr(mesh, "faces") else 0

    print("vertices:", vertices)
    print("faces:", faces)

    if vertices > 0 and faces > 0:
        print("[OK] readable non-empty mesh")
    else:
        print("[BAD] empty mesh")
        ok = False

raise SystemExit(0 if ok else 1)
