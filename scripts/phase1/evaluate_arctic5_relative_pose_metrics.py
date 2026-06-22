#!/usr/bin/env python
from pathlib import Path
import numpy as np
import pandas as pd
import trimesh

ROOT = Path("/home/fredcui/Projects/FollowMyHold")
PERF_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance")
MANIFEST = PERF_OUT / "arctic5_selector_performance_manifest.csv"
CASE_META = ROOT / "docs/phase0/arctic_phase017_selected_cases.csv"
OUT = PERF_OUT / "arctic5_relative_pose_metrics.csv"

def load_vertices(path):
    geom = trimesh.load(path, process=False)
    if isinstance(geom, trimesh.Scene):
        geom = trimesh.util.concatenate(tuple(geom.geometry.values()))
    return np.asarray(geom.vertices, dtype=np.float64)

def umeyama(src, dst):
    src = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)

    mu_s = src.mean(axis=0)
    mu_d = dst.mean(axis=0)

    X = src - mu_s
    Y = dst - mu_d

    cov = (Y.T @ X) / len(src)
    U, D, Vt = np.linalg.svd(cov)

    S = np.eye(3)
    if np.linalg.det(U @ Vt) < 0:
        S[-1, -1] = -1

    R = U @ S @ Vt
    scale = np.trace(np.diag(D) @ S) / max((X ** 2).sum() / len(src), 1e-12)
    t = mu_d - scale * (R @ mu_s)

    return scale, R, t

def apply(x, scale, R, t):
    return scale * (x @ R.T) + t

manifest = pd.read_csv(MANIFEST)
meta = pd.read_csv(CASE_META)

df = manifest.merge(meta, on="case", how="left", suffixes=("", "_meta"))

rows = []

for _, r in df.iterrows():
    base = {
        "case": r["case"],
        "method": r["method"],
        "run_id": r["run_id"],
        "exists": bool(r["exists"]),
    }

    if not bool(r["exists"]):
        base["status"] = "missing_prediction"
        rows.append(base)
        continue

    gt_processed = Path(f"/home/fredcui/Projects/arctic/outputs/processed_verts/seqs/{r['subject']}/{r['seq_name']}.npy")

    if not gt_processed.exists():
        base["status"] = "missing_gt"
        rows.append(base)
        continue

    try:
        gt = np.load(gt_processed, allow_pickle=True)
        if gt.shape == ():
            gt = gt.item()

        frame = int(r["frame"])
        view = int(r["view_id"])

        gt_obj = gt["cam_coord"]["verts.object"][frame, view]
        gt_left = gt["cam_coord"]["verts.left"][frame, view]
        gt_right = gt["cam_coord"]["verts.right"][frame, view]

        pred_hand = load_vertices(r["hand_mesh"])
        pred_obj = load_vertices(r["object_mesh"])

        candidates = []
        for side, gt_hand in [("left", gt_left), ("right", gt_right)]:
            n = min(len(pred_hand), len(gt_hand))

            scale, R, t = umeyama(pred_hand[:n], gt_hand[:n])

            aligned_hand = apply(pred_hand, scale, R, t)
            aligned_obj = apply(pred_obj, scale, R, t)

            pred_hand_center = aligned_hand.mean(axis=0)
            pred_obj_center = aligned_obj.mean(axis=0)

            gt_hand_center = gt_hand.mean(axis=0)
            gt_obj_center = gt_obj.mean(axis=0)

            pred_rel = pred_obj_center - pred_hand_center
            gt_rel = gt_obj_center - gt_hand_center

            rel_err_m = np.linalg.norm(pred_rel - gt_rel)

            candidates.append({
                "chosen_gt_hand": side,
                "sim_scale": float(scale),
                "pred_obj_to_hand_center_mm": float(np.linalg.norm(pred_rel) * 1000.0),
                "gt_obj_to_hand_center_mm": float(np.linalg.norm(gt_rel) * 1000.0),
                "relative_object_center_error_mm": float(rel_err_m * 1000.0),
                "pred_rel_x_mm": float(pred_rel[0] * 1000.0),
                "pred_rel_y_mm": float(pred_rel[1] * 1000.0),
                "pred_rel_z_mm": float(pred_rel[2] * 1000.0),
                "gt_rel_x_mm": float(gt_rel[0] * 1000.0),
                "gt_rel_y_mm": float(gt_rel[1] * 1000.0),
                "gt_rel_z_mm": float(gt_rel[2] * 1000.0),
            })

        best = sorted(candidates, key=lambda x: x["relative_object_center_error_mm"])[0]
        base.update({"status": "ok"})
        base.update(best)

    except Exception as e:
        base["status"] = "error"
        base["error"] = repr(e)

    rows.append(base)

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(out[[
    "case", "method", "status",
    "relative_object_center_error_mm",
    "pred_obj_to_hand_center_mm",
    "gt_obj_to_hand_center_mm"
]].to_string(index=False))
