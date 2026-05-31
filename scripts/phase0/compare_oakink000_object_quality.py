from pathlib import Path
import trimesh
import numpy as np

run = Path.home() / "foho_phase0/runs/oakink_000_baseline"

cases = {
    "initial_hunyuan": run / "hunyuan_hoi_out/test_hoi_mesh.ply",
    "final_obj": run / "guidance_out/test_obj.ply",
    "fallback_selected_obj": run / "fallback_out/selected_obj.ply",
}

print("case,exists,vertices,faces,components,watertight,largest_face_ratio,fragmentation_score")

for name, path in cases.items():
    if not path.exists():
        print(f"{name},False,,,,,,")
        continue

    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest_ratio = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0.0
    frag = (len(comps) - 1) + (1.0 - largest_ratio)

    print(
        f"{name},True,{len(mesh.vertices)},{len(mesh.faces)},"
        f"{len(comps)},{mesh.is_watertight},{largest_ratio:.6f},{frag:.6f}"
    )
