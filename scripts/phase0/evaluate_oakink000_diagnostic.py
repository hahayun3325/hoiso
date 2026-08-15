from pathlib import Path
import argparse
import csv
import numpy as np
import trimesh
from scipy.spatial import cKDTree

HOME = Path.home()

def load_mesh(path):
    path = Path(path)
    if not path.exists():
        return None
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def frag_score(mesh):
    if mesh is None or len(mesh.faces) == 0:
        return {
            "exists": False,
            "verts": 0,
            "faces": 0,
            "components": 999,
            "largest_face_ratio": 0.0,
            "fragmentation_score": 999.0,
            "watertight": False,
        }

    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest = float(faces.max() / max(len(mesh.faces), 1)) if len(faces) else 0.0

    return {
        "exists": True,
        "verts": len(mesh.vertices),
        "faces": len(mesh.faces),
        "components": len(comps),
        "largest_face_ratio": largest,
        "fragmentation_score": float((len(comps) - 1) + (1.0 - largest)),
        "watertight": bool(mesh.is_watertight),
    }

def sample_vertices(mesh, max_n=20000):
    pts = np.asarray(mesh.vertices)
    if len(pts) > max_n:
        rng = np.random.default_rng(0)
        pts = pts[rng.choice(len(pts), max_n, replace=False)]
    return pts

def hand_object_distance(hand, obj):
    if hand is None or obj is None:
        return {
            "center_dist": "",
            "min_dist": "",
            "mean_hand_to_obj": "",
            "p05_hand_to_obj": "",
        }

    hp = sample_vertices(hand)
    op = sample_vertices(obj)
    tree = cKDTree(op)
    d, _ = tree.query(hp, k=1)

    center_dist = float(np.linalg.norm(hand.vertices.mean(axis=0) - obj.vertices.mean(axis=0)))

    return {
        "center_dist": center_dist,
        "min_dist": float(np.min(d)),
        "mean_hand_to_obj": float(np.mean(d)),
        "p05_hand_to_obj": float(np.percentile(d, 5)),
    }

def find_final_meshes(run):
    candidates_obj = [
        run / "guidance_out/oakink_obj.ply",
        run / "guidance_out/test_obj.ply",
    ]
    candidates_hand = [
        run / "guidance_out/oakink_hand.ply",
        run / "guidance_out/test_hand.ply",
    ]

    obj = next((p for p in candidates_obj if p.exists()), None)
    hand = next((p for p in candidates_hand if p.exists()), None)
    return obj, hand

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", default=str(HOME / "foho_phase0/inspection/oakink_000/oakink000_diagnostic_metrics.csv"))
    args = ap.parse_args()

    rows = []

    for run_id in args.runs:
        run = HOME / "foho_phase0/runs" / run_id
        obj_path, hand_path = find_final_meshes(run)

        obj = load_mesh(obj_path) if obj_path else None
        hand = load_mesh(hand_path) if hand_path else None

        obj_stats = frag_score(obj)
        hand_stats = frag_score(hand)
        dist = hand_object_distance(hand, obj)

        row = {
            "run_id": run_id,
            "run_dir_exists": run.exists(),
            "obj_path": str(obj_path) if obj_path else "",
            "hand_path": str(hand_path) if hand_path else "",
        }

        for k, v in obj_stats.items():
            row[f"obj_{k}"] = v
        for k, v in hand_stats.items():
            row[f"hand_{k}"] = v
        row.update(dist)

        rows.append(row)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = sorted(set().union(*[r.keys() for r in rows]))
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("[OK] wrote", out)
    for r in rows:
        print(
            r["run_id"],
            "obj_frag=", r["obj_fragmentation_score"],
            "obj_comp=", r["obj_components"],
            "mean_hand_obj=", r["mean_hand_to_obj"],
        )

if __name__ == "__main__":
    main()
