from pathlib import Path
import trimesh
import numpy as np

cases = {
    "smoke015_hunyuan_initial": Path.home() / "foho_phase0/runs/smoke_015_prompt_rect/hunyuan_hoi_out/test_hoi_mesh.ply",
    "smoke019_exported_obj": Path.home() / "foho_phase0/runs/smoke_019_prompt_rect_guidance_transform_debug/guidance_out/test_obj.ply",
    "smoke021_exported_obj": Path.home() / "foho_phase0/runs/smoke_021_verified_freeze_obj_noise/guidance_out/test_obj.ply",
    "smoke022_exported_obj": Path.home() / "foho_phase0/runs/smoke_022_freeze_obj_pose_and_noise/guidance_out/test_obj.ply",
}

print("case,vertices,faces,components,watertight,largest_face_ratio,fragmentation_score")

for name, path in cases.items():
    if not path.exists():
        print(f"{name},MISSING,,,,,")
        continue

    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    comps = mesh.split(only_watertight=False)
    comp_faces = np.array([len(c.faces) for c in comps], dtype=np.float64)

    largest_ratio = comp_faces.max() / max(len(mesh.faces), 1) if len(comp_faces) else 0.0
    fragmentation_score = (len(comps) - 1) + (1.0 - largest_ratio)

    print(
        f"{name},{len(mesh.vertices)},{len(mesh.faces)},"
        f"{len(comps)},{mesh.is_watertight},"
        f"{largest_ratio:.6f},{fragmentation_score:.6f}"
    )
