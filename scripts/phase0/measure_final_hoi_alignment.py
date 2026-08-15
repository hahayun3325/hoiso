from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree

HOME = Path.home()

runs = [
    "oakink000_gemini31pro_short_selector_auto_frag_final",
    "oakink000_sonnet46thinking_short_selector_auto_frag_final",
    "oakink000_gpt55_short_selector_auto_frag_final",
    "oakink000_gpt55thinking_short_selector_auto_frag_final",
]

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def sample(mesh, n=20000):
    pts, _ = trimesh.sample.sample_surface(mesh, min(n, max(len(mesh.faces), 1)))
    return pts

for run_id in runs:
    run = HOME / "foho_phase0/runs" / run_id
    obj_path = run / "guidance_out/oakink_obj.ply"
    hand_path = run / "guidance_out/oakink_hand.ply"

    print("")
    print("=====", run_id, "=====")

    if not obj_path.exists() or not hand_path.exists():
        print("[MISSING]", obj_path, hand_path)
        continue

    obj = load_mesh(obj_path)
    hand = load_mesh(hand_path)

    obj_pts = sample(obj)
    hand_pts = sample(hand)

    tree = cKDTree(obj_pts)
    dists, _ = tree.query(hand_pts, k=1)

    print("obj:", obj_path)
    print("hand:", hand_path)
    print("min_dist:", float(np.min(dists)))
    print("mean_dist:", float(np.mean(dists)))
    print("p05_dist:", float(np.percentile(dists, 5)))
    print("p50_dist:", float(np.percentile(dists, 50)))
