from pathlib import Path
import trimesh
import numpy as np
from scipy.spatial import cKDTree

cases = {
    "013_final_obj": Path.home() / "foho_phase0/runs/smoke_013_octree192_guidance/guidance_out/test_obj.ply",
    "015_hunyuan_hoi": Path.home() / "foho_phase0/runs/smoke_015_prompt_rect/hunyuan_hoi_out/test_hoi_mesh.ply",
    "016_final_obj_octree128": Path.home() / "foho_phase0/runs/smoke_016_prompt_rect_guidance_ultralow/guidance_out/test_obj.ply",
    "017_final_obj_octree192": Path.home() / "foho_phase0/runs/smoke_017_prompt_rect_guidance_octree192_steps6/guidance_out/test_obj.ply",
}

def load_points(path, n=20000):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

    pts, _ = trimesh.sample.sample_surface(mesh, n)

    center = pts.mean(axis=0)
    pts = pts - center

    scale = np.linalg.norm(pts.max(axis=0) - pts.min(axis=0))
    pts = pts / max(scale, 1e-8)
    return pts

def chamfer(a, b):
    tree_a = cKDTree(a)
    tree_b = cKDTree(b)

    d_ab, _ = tree_b.query(a, k=1)
    d_ba, _ = tree_a.query(b, k=1)

    return float((d_ab ** 2).mean() + (d_ba ** 2).mean())

points = {}

for name, path in cases.items():
    if not path.exists():
        print("[MISSING]", name, path)
        continue
    points[name] = load_points(path)

names = list(points.keys())

print("pair,normalized_chamfer")
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        score = chamfer(points[names[i]], points[names[j]])
        print(f"{names[i]}__vs__{names[j]},{score:.8f}")
