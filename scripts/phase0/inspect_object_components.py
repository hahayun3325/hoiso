from pathlib import Path
import trimesh
import numpy as np

cases = {
    "smoke013_final_obj": Path.home() / "foho_phase0/runs/smoke_013_octree192_guidance/guidance_out/test_obj.ply",
    "smoke016_final_obj": Path.home() / "foho_phase0/runs/smoke_016_prompt_rect_guidance_ultralow/guidance_out/test_obj.ply",
    "smoke017_final_obj": Path.home() / "foho_phase0/runs/smoke_017_prompt_rect_guidance_octree192_steps6/guidance_out/test_obj.ply",
}

out_dir = Path.home() / "foho_phase0/inspection/prompt_ablation/components"
out_dir.mkdir(parents=True, exist_ok=True)

for name, path in cases.items():
    print(f"\n===== {name} =====")
    if not path.exists():
        print("[MISSING]", path)
        continue

    mesh = trimesh.load(path, process=False)
    comps = mesh.split(only_watertight=False)

    print("path:", path)
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

    for i, v, f, area, diag, extent in rows[:10]:
        print(
            f"component={i}, vertices={v}, faces={f}, "
            f"area={area:.6f}, diag={diag:.6f}, extent={np.round(extent, 6).tolist()}"
        )

    # Export largest 3 components for visual checking.
    for rank, (i, v, f, area, diag, extent) in enumerate(rows[:3]):
        out = out_dir / f"{name}_component_rank{rank}_orig{i}.ply"
        comps[i].export(out)
        print("[OK] exported", out)
