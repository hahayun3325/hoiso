from pathlib import Path
import argparse
import csv
import pickle
import numpy as np
import trimesh
from scipy.spatial import cKDTree

HOME = Path.home()

RUNS = {
    "baseline": "oakink000_default_short",
    "gpt55_selector": "oakink000_gpt55_short_selector_auto_frag_v7_truefile",
}

GT_DIR = HOME / "foho_phase0/inspection/oakink_000/gt_assets/oakink_image_annotation/selected_south_east_frame90"
GT_OBJ_PATH = HOME / "foho_phase0/inspection/oakink_000/gt_assets/A01023.obj"

def load_pkl(path):
    with open(path, "rb") as f:
        return pickle.load(f)

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def find_pred_meshes(run_dir):
    obj_candidates = [
        run_dir / "guidance_out/oakink_obj.ply",
        run_dir / "guidance_out/test_obj.ply",
    ]
    hand_candidates = [
        run_dir / "guidance_out/oakink_hand.ply",
        run_dir / "guidance_out/test_hand.ply",
    ]
    obj = next((p for p in obj_candidates if p.exists()), None)
    hand = next((p for p in hand_candidates if p.exists()), None)
    return hand, obj

def transform_points(points, s, R, t):
    return s * (points @ R.T) + t

def umeyama(src, dst, with_scale=True):
    """
    Find similarity transform mapping src -> dst.
    src, dst: Nx3
    returns s, R, t
    """
    src = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)
    assert src.shape == dst.shape and src.shape[1] == 3

    mu_src = src.mean(axis=0)
    mu_dst = dst.mean(axis=0)

    X = src - mu_src
    Y = dst - mu_dst

    cov = (Y.T @ X) / len(src)
    U, D, Vt = np.linalg.svd(cov)

    S = np.eye(3)
    if np.linalg.det(U @ Vt) < 0:
        S[-1, -1] = -1

    R = U @ S @ Vt

    if with_scale:
        var_src = (X ** 2).sum() / len(src)
        scale = np.trace(np.diag(D) @ S) / max(var_src, 1e-12)
    else:
        scale = 1.0

    t = mu_dst - scale * (R @ mu_src)
    return float(scale), R, t

def similarity_icp(src, dst, iters=20):
    """
    Similarity ICP mapping src -> dst using nearest-neighbor matches.
    Returns cumulative s, R, t.
    """
    src0 = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)

    tree = cKDTree(dst)
    curr = src0.copy()

    s_total = 1.0
    R_total = np.eye(3)
    t_total = np.zeros(3)

    for _ in range(iters):
        _, idx = tree.query(curr, k=1)
        matched = dst[idx]

        s, R, t = umeyama(curr, matched, with_scale=True)
        curr = transform_points(curr, s, R, t)

        # compose new transform with previous transform
        s_total_new = s * s_total
        R_total_new = R @ R_total
        t_total_new = s * (R @ t_total) + t

        s_total, R_total, t_total = s_total_new, R_total_new, t_total_new

    return s_total, R_total, t_total, curr

def sample_surface(mesh, n=30000, seed=0):
    rng = np.random.default_rng(seed)
    try:
        pts, _ = trimesh.sample.sample_surface(mesh, n)
        return np.asarray(pts, dtype=np.float64)
    except Exception:
        pts = np.asarray(mesh.vertices, dtype=np.float64)
        if len(pts) > n:
            pts = pts[rng.choice(len(pts), n, replace=False)]
        return pts

def sample_vertices(points, n=30000, seed=0):
    pts = np.asarray(points, dtype=np.float64)
    if len(pts) > n:
        rng = np.random.default_rng(seed)
        pts = pts[rng.choice(len(pts), n, replace=False)]
    return pts

def nn_dist(src, dst):
    tree = cKDTree(dst)
    d, _ = tree.query(src, k=1)
    return d

def fscore(d_pred_gt, d_gt_pred, tau):
    precision = float((d_pred_gt < tau).mean())
    recall = float((d_gt_pred < tau).mean())
    if precision + recall < 1e-12:
        return 0.0, precision, recall
    return float(2 * precision * recall / (precision + recall)), precision, recall

def component_stats(mesh):
    comps = mesh.split(only_watertight=False)
    face_counts = np.array([len(c.faces) for c in comps], dtype=np.float64)
    largest = float(face_counts.max() / max(len(mesh.faces), 1)) if len(face_counts) else 0.0
    frag = float((len(comps) - 1) + (1.0 - largest))
    return len(comps), largest, frag, bool(mesh.is_watertight)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HOME / "foho_phase0/inspection/oakink_000/oakink000_paper_like_metrics.csv"))
    ap.add_argument("--align_mode", choices=["mano_correspondence", "similarity_icp"], default="mano_correspondence")
    args = ap.parse_args()

    gt_hand_v = np.asarray(load_pkl(GT_DIR / "hand_v.pkl"), dtype=np.float64)
    T_obj = np.asarray(load_pkl(GT_DIR / "obj_transf.pkl"), dtype=np.float64)

    gt_obj_mesh = load_mesh(GT_OBJ_PATH)
    gt_obj_vertices = np.asarray(gt_obj_mesh.vertices, dtype=np.float64)
    gt_obj_vertices_h = np.concatenate([gt_obj_vertices, np.ones((len(gt_obj_vertices), 1))], axis=1)
    gt_obj_vertices_cam = (T_obj @ gt_obj_vertices_h.T).T[:, :3]
    gt_obj_mesh_cam = gt_obj_mesh.copy()
    gt_obj_mesh_cam.vertices = gt_obj_vertices_cam

    gt_obj_pts = sample_surface(gt_obj_mesh_cam, n=30000, seed=10)

    rows = []

    for label, run_id in RUNS.items():
        run_dir = HOME / "foho_phase0/runs" / run_id
        pred_hand_path, pred_obj_path = find_pred_meshes(run_dir)

        row = {
            "label": label,
            "run_id": run_id,
            "pred_hand_path": str(pred_hand_path) if pred_hand_path else "",
            "pred_obj_path": str(pred_obj_path) if pred_obj_path else "",
            "align_mode": args.align_mode,
        }

        if pred_hand_path is None or pred_obj_path is None:
            row["status"] = "missing_prediction"
            rows.append(row)
            continue

        pred_hand = load_mesh(pred_hand_path)
        pred_obj = load_mesh(pred_obj_path)

        pred_hand_v = np.asarray(pred_hand.vertices, dtype=np.float64)

        if args.align_mode == "mano_correspondence" and pred_hand_v.shape == gt_hand_v.shape:
            s, R, t = umeyama(pred_hand_v, gt_hand_v, with_scale=True)
            aligned_hand_v = transform_points(pred_hand_v, s, R, t)
        else:
            s, R, t, aligned_hand_v = similarity_icp(pred_hand_v, gt_hand_v, iters=25)

        pred_obj_v = np.asarray(pred_obj.vertices, dtype=np.float64)
        aligned_obj_v = transform_points(pred_obj_v, s, R, t)

        pred_obj_aligned = pred_obj.copy()
        pred_obj_aligned.vertices = aligned_obj_v

        pred_obj_pts = sample_surface(pred_obj_aligned, n=30000, seed=20)

        d_pred_gt = nn_dist(pred_obj_pts, gt_obj_pts)
        d_gt_pred = nn_dist(gt_obj_pts, pred_obj_pts)

        cd_m = float((d_pred_gt.mean() + d_gt_pred.mean()) / 2.0)
        cd_mm = cd_m * 1000.0

        f5, p5, r5 = fscore(d_pred_gt, d_gt_pred, 0.005)
        f10, p10, r10 = fscore(d_pred_gt, d_gt_pred, 0.010)

        hand_nn = nn_dist(aligned_hand_v, gt_hand_v)
        hand_rmse = float(np.sqrt((hand_nn ** 2).mean()))

        comps, largest, frag, watertight = component_stats(pred_obj)

        row.update({
            "status": "ok",
            "sim_scale": s,
            "hand_align_rmse_m": hand_rmse,
            "hand_align_rmse_mm": hand_rmse * 1000.0,
            "object_cd_m": cd_m,
            "object_cd_mm": cd_mm,
            "f5": f5,
            "f10": f10,
            "precision_5mm": p5,
            "recall_5mm": r5,
            "precision_10mm": p10,
            "recall_10mm": r10,
            "pred_obj_components": comps,
            "pred_obj_largest_face_ratio": largest,
            "pred_obj_fragmentation": frag,
            "pred_obj_watertight": watertight,
        })

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
            r["label"],
            "status=", r.get("status"),
            "CD(mm)=", r.get("object_cd_mm"),
            "F5=", r.get("f5"),
            "F10=", r.get("f10"),
            "frag=", r.get("pred_obj_fragmentation"),
            "hand_rmse(mm)=", r.get("hand_align_rmse_mm"),
        )

if __name__ == "__main__":
    main()
