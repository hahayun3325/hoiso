#!/usr/bin/env python
from pathlib import Path
import numpy as np
import pandas as pd
import trimesh
from scipy.spatial import cKDTree

ROOT = Path("/home/fredcui/Projects/FollowMyHold")
EXP_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance")
MANIFEST = EXP_OUT / "arctic5_selector_performance_manifest.csv"
CASE_META = ROOT / "docs/phase0/arctic_phase017_selected_cases.csv"
OUT = EXP_OUT / "arctic5_selector_gt_metrics.csv"

def load_mesh_vertices(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return np.asarray(mesh.vertices, dtype=np.float64)

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

def cd_fscore(pred, gt, thresholds=(0.005, 0.01)):
    pred = np.asarray(pred)
    gt = np.asarray(gt)

    d1, _ = cKDTree(gt).query(pred)
    d2, _ = cKDTree(pred).query(gt)

    out = {
        "cd_m": float(0.5 * (d1.mean() + d2.mean())),
        "pred_to_gt_m": float(d1.mean()),
        "gt_to_pred_m": float(d2.mean()),
    }

    for th in thresholds:
        key = int(th * 1000)
        p = float((d1 < th).mean())
        r = float((d2 < th).mean())
        f = 2 * p * r / max(p + r, 1e-12)
        out[f"f{key}"] = f
        out[f"precision{key}"] = p
        out[f"recall{key}"] = r

    return out

manifest = pd.read_csv(MANIFEST)
meta = pd.read_csv(CASE_META)

df = manifest.merge(meta, on="case", how="left", suffixes=("", "_meta"))

rows = []

for _, row in df.iterrows():
    case = row["case"]
    method = row["method"]

    base = {
        "case": case,
        "method": method,
        "run_id": row["run_id"],
        "exists": bool(row["exists"]),
        "hand_mesh": row.get("hand_mesh", ""),
        "object_mesh": row.get("object_mesh", ""),
    }

    if not bool(row["exists"]):
        base["status"] = "missing_prediction"
        rows.append(base)
        continue

    gt_processed = Path(f"/home/fredcui/Projects/arctic/outputs/processed_verts/seqs/{row['subject']}/{row['seq_name']}.npy")

    if not gt_processed.exists():
        base["status"] = "missing_gt"
        base["gt_processed"] = str(gt_processed)
        rows.append(base)
        continue

    try:
        gt = np.load(gt_processed, allow_pickle=True)
        if gt.shape == ():
            gt = gt.item()

        frame = int(row["frame"])
        view = int(row["view_id"])

        gt_obj = gt["cam_coord"]["verts.object"][frame, view]
        gt_left = gt["cam_coord"]["verts.left"][frame, view]
        gt_right = gt["cam_coord"]["verts.right"][frame, view]

        pred_hand = load_mesh_vertices(row["hand_mesh"])
        pred_obj = load_mesh_vertices(row["object_mesh"])

        candidates = []
        for side, gt_hand in [("left", gt_left), ("right", gt_right)]:
            n = min(len(pred_hand), len(gt_hand))
            scale, R, t = umeyama(pred_hand[:n], gt_hand[:n])
            aligned_hand = apply(pred_hand, scale, R, t)
            aligned_obj = apply(pred_obj, scale, R, t)

            hand_m = cd_fscore(aligned_hand, gt_hand)
            obj_m = cd_fscore(aligned_obj, gt_obj)
            candidates.append((hand_m["cd_m"], side, scale, hand_m, obj_m))

        candidates.sort(key=lambda x: x[0])
        hand_cd, side, scale, hand_m, obj_m = candidates[0]

        base.update({
            "status": "ok",
            "subject": row["subject"],
            "seq_name": row["seq_name"],
            "frame": frame,
            "view_id": view,
            "gt_processed": str(gt_processed),
            "chosen_gt_hand": side,
            "sim_scale": float(scale),
            "hand_cd_mm": hand_m["cd_m"] * 1000.0,
            "object_cd_mm": obj_m["cd_m"] * 1000.0,
            "object_f5": obj_m["f5"],
            "object_f10": obj_m["f10"],
            "object_precision_5mm": obj_m["precision5"],
            "object_recall_5mm": obj_m["recall5"],
            "object_precision_10mm": obj_m["precision10"],
            "object_recall_10mm": obj_m["recall10"],
        })

    except Exception as e:
        base["status"] = "error"
        base["error"] = repr(e)

    rows.append(base)

out = pd.DataFrame(rows)
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(out[[
    "case", "method", "status", "object_cd_mm", "object_f5", "object_f10", "hand_cd_mm"
]].to_string(index=False))
