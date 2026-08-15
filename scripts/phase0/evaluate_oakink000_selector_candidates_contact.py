from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree
import csv

HOME = Path.home()

RUNS = {
    "baseline": "oakink000_default_short",
    "gpt55_selector": "oakink000_gpt55_short_selector_auto_frag_v7_truefile",
}

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def sample_vertices(mesh, n=20000):
    pts = np.asarray(mesh.vertices)
    if len(pts) > n:
        rng = np.random.default_rng(0)
        pts = pts[rng.choice(len(pts), n, replace=False)]
    return pts

def contact_stats(hand, obj):
    hp = sample_vertices(hand)
    op = sample_vertices(obj)
    tree = cKDTree(op)
    d, _ = tree.query(hp, k=1)
    return {
        "min_dist": float(d.min()),
        "p01_dist": float(np.percentile(d, 1)),
        "p05_dist": float(np.percentile(d, 5)),
        "mean_dist": float(d.mean()),
        "center_dist": float(np.linalg.norm(hand.vertices.mean(axis=0) - obj.vertices.mean(axis=0))),
    }

rows = []
for label, run_id in RUNS.items():
    run = HOME / "foho_phase0/runs" / run_id
    hand_path = run / "guidance_out/oakink_hand.ply"
    obj_path = run / "guidance_out/oakink_obj.ply"

    if not hand_path.exists() or not obj_path.exists():
        print("[MISS]", run_id, hand_path, obj_path)
        continue

    hand = load_mesh(hand_path)
    obj = load_mesh(obj_path)
    row = {"label": label, "run_id": run_id, "hand": str(hand_path), "obj": str(obj_path)}
    row.update(contact_stats(hand, obj))
    rows.append(row)

out = HOME / "foho_phase0/inspection/oakink_000/oakink000_contact_stats_baseline_vs_gpt55_selector.csv"
out.parent.mkdir(parents=True, exist_ok=True)

with open(out, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print("[OK] wrote", out)
for r in rows:
    print(r)
