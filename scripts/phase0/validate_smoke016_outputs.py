from pathlib import Path
import trimesh

base = Path.home() / "foho_phase0/runs/smoke_016_prompt_rect_guidance_ultralow/guidance_out"

paths = {
    "object": base / "test_obj.ply",
    "hand": base / "test_hand.ply",
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
    print("vertices:", len(mesh.vertices) if hasattr(mesh, "vertices") else "NA")
    print("faces:", len(mesh.faces) if hasattr(mesh, "faces") else "NA")
    print("bounds:", mesh.bounds if hasattr(mesh, "bounds") else "NA")
    print("watertight:", mesh.is_watertight if hasattr(mesh, "is_watertight") else "NA")

    if hasattr(mesh, "vertices") and len(mesh.vertices) > 0:
        print("[OK] readable non-empty mesh")
    else:
        print("[BAD] empty mesh")
        ok = False

raise SystemExit(0 if ok else 1)
