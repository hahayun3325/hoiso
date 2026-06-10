from pathlib import Path
import numpy as np
import pandas as pd
import trimesh
from scipy.spatial import cKDTree

HOME = Path.home()
GT_P = Path("/home/fredcui/Projects/arctic/outputs/processed_verts/seqs/s01/ketchup_grab_01.npy")
FRAME = 147
VIEW = 7

RUN_ROOT = HOME / "foho_phase0/runs"
OUT_DIR = HOME / "foho_phase0/inspection/arctic_phase017/first_metric_dryrun_aket01"
OUT_DIR.mkdir(parents=True, exist_ok=True)

METHOD_ROOTS = {
    "default": RUN_ROOT / "arctic_aket01_default",
    "gpt55_selector": RUN_ROOT / "arctic_aket01_gpt55_auto_selector_native_v2",
}

def find_mesh(root, kind):
    if not root.exists():
        return None
    pats = ["*.ply", "*.obj"]
    files = []
    for pat in pats:
        files.extend(root.rglob(pat))
    files = [p for p in files if kind in p.name.lower()]
    if not files:
        return None
    # Prefer final/guidance outputs if available.
    files = sorted(files, key=lambda p: ("final" not in str(p).lower(), "guidance" not in str(p).lower(), len(str(p))))
    return files[0]

def load_vertices(p):
    mesh = trimesh.load(p, process=False)
    if hasattr(mesh, "vertices"):
        return np.asarray(mesh.vertices, dtype=np.float64)
    raise RuntimeError(f"Cannot load vertices from {p}")

def umeyama_align(src, dst, with_scale=True):
    """
    Return scale, R, t mapping src -> dst.
    src and dst must have same shape.
    """
    src = np.asarray(src, dtype=np.float64)
    dst = np.asarray(dst, dtype=np.float64)

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
    return scale, R, t

def apply_sim(x, scale, R, t):
    return scale * (x @ R.T) + t

def chamfer_and_fscore(pred, gt, thresholds=(0.005, 0.01)):
    pred = np.asarray(pred)
    gt = np.asarray(gt)

    tree_gt = cKDTree(gt)
    d_pred, _ = tree_gt.query(pred, k=1)

    tree_pred = cKDTree(pred)
    d_gt, _ = tree_pred.query(gt, k=1)

    cd = 0.5 * (d_pred.mean() + d_gt.mean())

    out = {
        "cd": float(cd),
        "pred_to_gt": float(d_pred.mean()),
        "gt_to_pred": float(d_gt.mean()),
    }

    for th in thresholds:
        precision = float((d_pred < th).mean())
        recall = float((d_gt < th).mean())
        f = 2 * precision * recall / max(precision + recall, 1e-12)
        out[f"fscore_{int(th*1000)}mm"] = f
        out[f"precision_{int(th*1000)}mm"] = precision
        out[f"recall_{int(th*1000)}mm"] = recall

    return out

gt = np.load(GT_P, allow_pickle=True)
if gt.shape == ():
    gt = gt.item()

gt_obj = gt["cam_coord"]["verts.object"][FRAME, VIEW]
gt_left = gt["cam_coord"]["verts.left"][FRAME, VIEW]
gt_right = gt["cam_coord"]["verts.right"][FRAME, VIEW]

rows = []

for method, root in METHOD_ROOTS.items():
    hand_p = find_mesh(root, "hand")
    obj_p = find_mesh(root, "obj")
    if obj_p is None:
        obj_p = find_mesh(root, "object")

    print("\n" + "=" * 80)
    print("method:", method)
    print("root:", root)
    print("hand:", hand_p)
    print("obj:", obj_p)

    if hand_p is None or obj_p is None:
        rows.append({
            "method": method,
            "status": "missing_pred_mesh",
            "hand_path": str(hand_p),
            "object_path": str(obj_p),
        })
        continue

    pred_hand = load_vertices(hand_p)
    pred_obj = load_vertices(obj_p)

    if pred_hand.shape[0] != 778:
        print("[WARN] pred hand vertex count is not 778:", pred_hand.shape)

    candidates = []
    for side, gt_hand in [("left", gt_left), ("right", gt_right)]:
        n = min(len(pred_hand), len(gt_hand))
        scale, R, t = umeyama_align(pred_hand[:n], gt_hand[:n], with_scale=True)
        aligned_hand = apply_sim(pred_hand, scale, R, t)
        aligned_obj = apply_sim(pred_obj, scale, R, t)

        hand_metric = chamfer_and_fscore(aligned_hand, gt_hand)
        obj_metric = chamfer_and_fscore(aligned_obj, gt_obj)

        candidates.append((hand_metric["cd"], side, scale, R, t, hand_metric, obj_metric, aligned_hand, aligned_obj))

    candidates.sort(key=lambda x: x[0])
    hand_cd, side, scale, R, t, hand_metric, obj_metric, aligned_hand, aligned_obj = candidates[0]

    # Export aligned meshes for visual debug.
    trimesh.Trimesh(vertices=aligned_hand, faces=trimesh.load(hand_p, process=False).faces, process=False).export(
        OUT_DIR / f"{method}_aligned_hand_to_gt_{side}.ply"
    )
    trimesh.Trimesh(vertices=aligned_obj, faces=trimesh.load(obj_p, process=False).faces, process=False).export(
        OUT_DIR / f"{method}_aligned_obj_to_gt_{side}.ply"
    )
    trimesh.Trimesh(vertices=gt_obj, process=False).export(OUT_DIR / "gt_object_points.ply")
    trimesh.Trimesh(vertices=gt_left, process=False).export(OUT_DIR / "gt_left_hand_points.ply")
    trimesh.Trimesh(vertices=gt_right, process=False).export(OUT_DIR / "gt_right_hand_points.ply")

    row = {
        "method": method,
        "status": "ok",
        "chosen_gt_hand": side,
        "sim_scale": scale,
        "hand_cd_m": hand_metric["cd"],
        "hand_cd_mm": hand_metric["cd"] * 1000.0,
        "object_cd_m": obj_metric["cd"],
        "object_cd_mm": obj_metric["cd"] * 1000.0,
        "object_f5": obj_metric["fscore_5mm"],
        "object_f10": obj_metric["fscore_10mm"],
        "hand_path": str(hand_p),
        "object_path": str(obj_p),
    }
    rows.append(row)
    print(row)

out_csv = OUT_DIR / "aket01_first_metric_dryrun.csv"
pd.DataFrame(rows).to_csv(out_csv, index=False)
print("\n[OK] wrote", out_csv)
print(pd.DataFrame(rows).to_string(index=False))
