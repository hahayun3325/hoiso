from pathlib import Path
import trimesh
import numpy as np

run = Path.home() / "foho_phase0/runs/smoke_017_prompt_rect_guidance_octree192_steps6"

paths = {
    "debug_final_obj": next((run / "foho_debug").rglob("final_obj_mesh.ply")),
    "exported_test_obj": run / "guidance_out/test_obj.ply",
}

for name, path in paths.items():
    mesh = trimesh.load(path, process=False)
    comps = mesh.split(only_watertight=False)

    print(f"\n===== {name} =====")
    print(path)
    print("vertices:", len(mesh.vertices))
    print("faces:", len(mesh.faces))
    print("components:", len(comps))
    print("bounds:", mesh.bounds)
    print("area:", mesh.area)
