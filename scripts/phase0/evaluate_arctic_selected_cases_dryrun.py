from pathlib import Path
import numpy as np
import pandas as pd
import trimesh
from scipy.spatial import cKDTree

HOME = Path.home()
MANIFEST = HOME / "foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases/arctic_selected_eval_mesh_manifest.csv"
OUT_DIR = HOME / "foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_mesh_vertices(path):
    mesh = trimesh.load(path, process=False)
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
        p = float((d1 < th).mean())
        r = float((d2 < th).mean())
        f = 2 * p * r / max(p + r, 1e-12)
        out[f"f{int(th*1000)}"] = f
        out[f"precision{int(th*1000)}"] = p
        out[f"recall{int(th*1000)}"] = r

    return out

rows = []
manifest = pd.read_csv(MANIFEST)

for _, row in manifest.iterrows():
    case = row["case"]
    method = row["method"]
    frame = int(row["frame"])
    view = int(row["view_id"])

    print("\n" + "=" * 80)
    print(case, method)

    if not row["hand_exists"] or not row["object_exists"]:
        rows.append({"case": case, "method": method, "status": "missing_prediction"})
        continue

    gt = np.load(row["gt_processed"], allow_pickle=True)
    if gt.shape == ():
        gt = gt.item()

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

    result = {
        "case": case,
        "method": method,
        "status": "ok",
        "chosen_gt_hand": side,
        "sim_scale": scale,
        "hand_cd_mm": hand_m["cd_m"] * 1000,
        "object_cd_mm": obj_m["cd_m"] * 1000,
        "object_f5": obj_m["f5"],
        "object_f10": obj_m["f10"],
        "hand_mesh": row["hand_mesh"],
        "object_mesh": row["object_mesh"],
    }

    print(result)
    rows.append(result)

out = pd.DataFrame(rows)
out_csv = OUT_DIR / "arctic_selected_cases_dryrun_metrics.csv"
out.to_csv(out_csv, index=False)

print("\n===== summary =====")
print(out.to_string(index=False))
print("[OK] wrote", out_csv)
