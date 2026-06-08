from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree
import csv

HOME = Path.home()
RUN_ID = "oakink000_gpt55_short_selector_auto_frag_v7_truefile"
RUN = HOME / "foho_phase0/runs" / RUN_ID
INSPECT = HOME / "foho_phase0/inspection/oakink_000" / RUN_ID / "internal_selector_debug"

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

hand_path = RUN / "guidance_out/oakink_hand.ply"
hand = load_mesh(hand_path)

candidates = {
    "selector_before": INSPECT / "selector_candidate_before_phase42.ply",
    "selector_after": INSPECT / "selector_candidate_phase42_before_joint.ply",
    "selector_after_true": INSPECT / "selector_candidate_phase42_before_joint_true.ply",
    "selector_selected": INSPECT / "selector_selected_before_joint.ply",
    "final_obj": RUN / "guidance_out/oakink_obj.ply",
}

rows = []
for name, path in candidates.items():
    if not path.exists():
        print("[MISS]", name, path)
        continue
    obj = load_mesh(path)
    row = {"stage": name, "obj_path": str(path), "hand_path": str(hand_path)}
    row.update(contact_stats(hand, obj))
    rows.append(row)

out = HOME / "foho_phase0/inspection/oakink_000/oakink000_gpt55_stage_contact_v2.csv"
out.parent.mkdir(parents=True, exist_ok=True)

with open(out, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print("[OK] wrote", out)
for r in rows:
    print(r)

print("\n===== compact =====")
for r in rows:
    print(r["stage"], "min=", r["min_dist"], "p05=", r["p05_dist"], "mean=", r["mean_dist"])
