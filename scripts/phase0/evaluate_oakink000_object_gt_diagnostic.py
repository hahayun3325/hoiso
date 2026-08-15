from pathlib import Path
import argparse
import csv
import numpy as np
import trimesh
from scipy.spatial import cKDTree

HOME = Path.home()

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def sample_surface(mesh, n=30000, seed=0):
    rng = np.random.default_rng(seed)
    try:
        pts, _ = trimesh.sample.sample_surface(mesh, n)
    except Exception:
        pts = np.asarray(mesh.vertices)
        if len(pts) > n:
            pts = pts[rng.choice(len(pts), n, replace=False)]
    return np.asarray(pts, dtype=np.float64)

def normalize_points(pts):
    pts = np.asarray(pts, dtype=np.float64)
    center = (pts.min(axis=0) + pts.max(axis=0)) / 2.0
    diag = np.linalg.norm(pts.max(axis=0) - pts.min(axis=0))
    if diag <= 1e-9:
        diag = 1.0
    return (pts - center) / diag

def nn_stats(src, tgt):
    tree = cKDTree(tgt)
    d, _ = tree.query(src, k=1)
    return d

def fscore(d1, d2, tau):
    r = float((d1 < tau).mean())
    p = float((d2 < tau).mean())
    if p + r <= 1e-12:
        return 0.0, p, r
    return 2 * p * r / (p + r), p, r

def object_metrics(pred_mesh, gt_mesh, n=30000):
    pred = normalize_points(sample_surface(pred_mesh, n=n, seed=1))
    gt = normalize_points(sample_surface(gt_mesh, n=n, seed=2))

    # shape-only diagnostic: center/scale normalized, not official hand-aligned metric
    d_pred_gt = nn_stats(pred, gt)
    d_gt_pred = nn_stats(gt, pred)

    cd = float(d_pred_gt.mean() + d_gt_pred.mean()) / 2.0
    cd2 = float((d_pred_gt ** 2).mean() + (d_gt_pred ** 2).mean()) / 2.0

    f1, p1, r1 = fscore(d_pred_gt, d_gt_pred, 0.01)
    f2, p2, r2 = fscore(d_pred_gt, d_gt_pred, 0.02)
    f5, p5, r5 = fscore(d_pred_gt, d_gt_pred, 0.05)

    comps = pred_mesh.split(only_watertight=False)
    face_counts = np.array([len(c.faces) for c in comps], dtype=float)
    largest_ratio = float(face_counts.max() / max(len(pred_mesh.faces), 1)) if len(face_counts) else 0.0

    return {
        "cd_l1_norm": cd,
        "cd_l2_norm": cd2,
        "fscore_tau_0.01": f1,
        "precision_tau_0.01": p1,
        "recall_tau_0.01": r1,
        "fscore_tau_0.02": f2,
        "precision_tau_0.02": p2,
        "recall_tau_0.02": r2,
        "fscore_tau_0.05": f5,
        "precision_tau_0.05": p5,
        "recall_tau_0.05": r5,
        "pred_vertices": len(pred_mesh.vertices),
        "pred_faces": len(pred_mesh.faces),
        "pred_components": len(comps),
        "pred_largest_face_ratio": largest_ratio,
        "pred_watertight": bool(pred_mesh.is_watertight),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt", default=str(HOME / "foho_phase0/inspection/oakink_000/gt_assets/A01023.obj"))
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--out", default=str(HOME / "foho_phase0/inspection/oakink_000/oakink000_object_gt_diagnostic_metrics.csv"))
    args = ap.parse_args()

    gt = load_mesh(args.gt)
    rows = []

    for run_id in args.runs:
        run = HOME / "foho_phase0/runs" / run_id
        pred_candidates = [
            run / "guidance_out/oakink_obj.ply",
            run / "guidance_out/test_obj.ply",
        ]
        pred_path = next((p for p in pred_candidates if p.exists()), None)

        row = {
            "run_id": run_id,
            "pred_path": str(pred_path) if pred_path else "",
            "gt_path": str(args.gt),
            "pred_exists": pred_path is not None,
        }

        if pred_path:
            pred = load_mesh(pred_path)
            row.update(object_metrics(pred, gt))

        rows.append(row)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    fields = sorted(set().union(*[r.keys() for r in rows]))
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    print("[OK] wrote", out)
    for r in rows:
        print(
            r["run_id"],
            "cd=", r.get("cd_l1_norm"),
            "f@0.02=", r.get("fscore_tau_0.02"),
            "components=", r.get("pred_components"),
        )

if __name__ == "__main__":
    main()
