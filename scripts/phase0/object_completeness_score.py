from pathlib import Path
import trimesh
import numpy as np

paths = {
    "smoke015_hunyuan_initial": Path.home() / "foho_phase0/runs/smoke_015_prompt_rect/hunyuan_hoi_out/test_hoi_mesh.ply",
    "smoke016_final_obj": Path.home() / "foho_phase0/runs/smoke_016_prompt_rect_guidance_ultralow/guidance_out/test_obj.ply",
    "smoke017_final_obj": Path.home() / "foho_phase0/runs/smoke_017_prompt_rect_guidance_octree192_steps6/guidance_out/test_obj.ply",
    "smoke019_before_h2m": next((Path.home() / "foho_phase0/runs/smoke_019_prompt_rect_guidance_transform_debug/foho_debug").rglob("debug_obj_before_hunyuan2moge.ply")),
    "smoke019_exported_obj": Path.home() / "foho_phase0/runs/smoke_019_prompt_rect_guidance_transform_debug/guidance_out/test_obj.ply",
}

print("case,vertices,faces,components,watertight,largest_face_ratio,fragmentation_score")

for name, path in paths.items():
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    comps = mesh.split(only_watertight=False)
    comp_faces = np.array([len(c.faces) for c in comps], dtype=np.float64)

    if len(comp_faces) == 0:
        largest_ratio = 0.0
    else:
        largest_ratio = comp_faces.max() / max(len(mesh.faces), 1)

    # Simple score: lower is better.
    # 0 means one component dominates.
    fragmentation_score = (len(comps) - 1) + (1.0 - largest_ratio)

    print(
        f"{name},{len(mesh.vertices)},{len(mesh.faces)},"
        f"{len(comps)},{mesh.is_watertight},"
        f"{largest_ratio:.6f},{fragmentation_score:.6f}"
    )
