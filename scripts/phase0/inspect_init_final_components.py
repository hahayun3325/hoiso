from pathlib import Path
import trimesh
import numpy as np

cases = {
    "smoke015_hunyuan_initial": Path.home() / "foho_phase0/runs/smoke_015_prompt_rect/hunyuan_hoi_out/test_hoi_mesh.ply",
    "smoke017_final_obj": Path.home() / "foho_phase0/runs/smoke_017_prompt_rect_guidance_octree192_steps6/guidance_out/test_obj.ply",
    "smoke017_final_hand": Path.home() / "foho_phase0/runs/smoke_017_prompt_rect_guidance_octree192_steps6/guidance_out/test_hand.ply",
}

for name, path in cases.items():
    print(f"\n===== {name} =====")
    print(path)

    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    comps = mesh.split(only_watertight=False)
    print("vertices:", len(mesh.vertices))
    print("faces:", len(mesh.faces))
    print("components:", len(comps))
    print("bounds:", mesh.bounds)
    print("watertight:", mesh.is_watertight)

    rows = []
    for i, c in enumerate(comps):
        extent = c.bounds[1] - c.bounds[0]
        diag = float(np.linalg.norm(extent))
        rows.append((i, len(c.vertices), len(c.faces), float(c.area), diag, extent))
    rows.sort(key=lambda x: x[2], reverse=True)

    for i, v, f, area, diag, extent in rows[:10]:
        print(
            f"component={i}, vertices={v}, faces={f}, "
            f"area={area:.6f}, diag={diag:.6f}, extent={np.round(extent, 6).tolist()}"
        )
