from pathlib import Path
import trimesh
import numpy as np

cases = {
    "smoke013_final_obj": Path.home() / "foho_phase0/runs/smoke_013_octree192_guidance/guidance_out/test_obj.ply",
    "smoke015_hunyuan_hoi": Path.home() / "foho_phase0/runs/smoke_015_prompt_rect/hunyuan_hoi_out/test_hoi_mesh.ply",
    "smoke016_final_obj_octree128": Path.home() / "foho_phase0/runs/smoke_016_prompt_rect_guidance_ultralow/guidance_out/test_obj.ply",
    "smoke017_final_obj_octree192": Path.home() / "foho_phase0/runs/smoke_017_prompt_rect_guidance_octree192_steps6/guidance_out/test_obj.ply",
    "smoke017_final_hand": Path.home() / "foho_phase0/runs/smoke_017_prompt_rect_guidance_octree192_steps6/guidance_out/test_hand.ply",
}

print("case,path,vertices,faces,watertight,extent,bbox_diag,surface_area")

for name, path in cases.items():
    if not path.exists():
        print(f'"{name}","MISSING","","","","","",""')
        continue

    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    bounds = mesh.bounds
    extent = bounds[1] - bounds[0]
    diag = float(np.linalg.norm(extent))

    row = [
        name,
        str(path),
        len(mesh.vertices),
        len(mesh.faces),
        bool(mesh.is_watertight),
        np.round(extent, 6).tolist(),
        round(diag, 6),
        round(float(mesh.area), 6),
    ]

    print(",".join(map(lambda x: f'"{x}"', row)))
