from pathlib import Path
import trimesh
import numpy as np

run = Path.home() / "foho_phase0/runs/smoke_018_prompt_rect_guidance_debug_exports"
paths = [
    run / "hunyuan_hoi_out/test_hoi_mesh.ply",
    *sorted((run / "foho_debug").rglob("*obj*.ply")),
    run / "guidance_out/test_obj.ply",
]

for path in paths:
    print(f"\n===== {path.relative_to(run)} =====")
    if not path.exists():
        print("[MISSING]")
        continue

    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    comps = mesh.split(only_watertight=False)

    print("vertices:", len(mesh.vertices))
    print("faces:", len(mesh.faces))
    print("components:", len(comps))
    print("watertight:", mesh.is_watertight)
    print("bounds:", mesh.bounds)

    rows = []
    for i, c in enumerate(comps):
        extent = c.bounds[1] - c.bounds[0]
        diag = float(np.linalg.norm(extent))
        rows.append((i, len(c.vertices), len(c.faces), float(c.area), diag, extent))

    rows.sort(key=lambda x: x[2], reverse=True)

    for i, v, f, area, diag, extent in rows[:8]:
        print(
            f"component={i}, vertices={v}, faces={f}, "
            f"area={area:.6f}, diag={diag:.6f}, extent={np.round(extent, 6).tolist()}"
        )
