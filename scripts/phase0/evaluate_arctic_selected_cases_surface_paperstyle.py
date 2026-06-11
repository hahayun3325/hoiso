from pathlib import Path
import numpy as np
import pandas as pd
import trimesh
from scipy.spatial import cKDTree

HOME = Path.home()
OUT_DIR = HOME / "foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases_surface"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MANIFEST = HOME / "foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases/arctic_selected_eval_mesh_manifest.csv"
SIDE_MAP = HOME / "foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases/arctic_selected_case_hand_side_map.csv"

N_SAMPLES = 20000
THRESHOLDS = (0.005, 0.01)  # meters: 5mm and 10mm

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def make_gt_object_mesh(gt, frame, view):
    verts = np.asarray(gt["cam_coord"]["verts.object"][frame, view], dtype=np.float64)

    # ARCTIC stores object faces in world_coord.
    faces = np.asarray(gt["world_coord"]["f"][frame], dtype=np.int64)
    f_len = int(gt["world_coord"]["f_len"][frame])
    v_len = int(gt["world_coord"]["v_len"][frame])

    verts = verts[:v_len]
    faces = faces[:f_len]

    # Safety for possible 1-indexed faces.
    if faces.min() == 1 and faces.max() == v_len:
        faces = faces - 1

    valid = (faces >= 0).all(axis=1) & (faces < len(verts)).all(axis=1)
    faces = faces[valid]

    return trimesh.Trimesh(vertices=verts, faces=faces, process=False)

def sample_surface(mesh, n, seed):
    np.random.seed(seed)
    mesh = mesh.copy()
    if mesh.faces is None or len(mesh.faces) == 0:
        pts = np.asarray(mesh.vertices, dtype=np.float64)
        if len(pts) > n:
            idx = np.linspace(0, len(pts) - 1, n).astype(int)
            pts = pts[idx]
        return pts
    pts, _ = trimesh.sample.sample_surface(mesh, n)
    return np.asarray(pts, dtype=np.float64)

def umeyama(src, dst, with_scale=True):
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

    if with_scale:
        scale = np.trace(np.diag(D) @ S) / max((X ** 2).sum() / len(src), 1e-12)
    else:
        scale = 1.0

    t = mu_d - scale * (R @ mu_s)
    return scale, R, t

def apply_sim(x, scale, R, t):
    return scale * (np.asarray(x) @ R.T) + t

def cd_fscore(pred_pts, gt_pts):
    d_pred, _ = cKDTree(gt_pts).query(pred_pts, k=1)
    d_gt, _ = cKDTree(pred_pts).query(gt_pts, k=1)

    out = {
        "cd_m": float(0.5 * (d_pred.mean() + d_gt.mean())),
        "pred_to_gt_m": float(d_pred.mean()),
        "gt_to_pred_m": float(d_gt.mean()),
    }

    for th in THRESHOLDS:
        precision = float((d_pred < th).mean())
        recall = float((d_gt < th).mean())
        f = 2.0 * precision * recall / max(precision + recall, 1e-12)
        key = int(th * 1000)
        out[f"precision_{key}mm"] = precision
        out[f"recall_{key}mm"] = recall
        out[f"fscore_{key}mm"] = f

    return out

manifest = pd.read_csv(MANIFEST)
side_df = pd.read_csv(SIDE_MAP)
side_map = dict(zip(side_df["case"], side_df["chosen_gt_hand"]))

rows = []

for _, row in manifest.iterrows():
    case = row["case"]
    method = row["method"]
    frame = int(row["frame"])
    view = int(row["view_id"])
    side = side_map[case]

    print("\n" + "=" * 80)
    print("case:", case, "method:", method, "fixed_gt_hand:", side)

    if not bool(row["hand_exists"]) or not bool(row["object_exists"]):
        rows.append({"case": case, "method": method, "status": "missing_prediction"})
        continue

    gt = np.load(row["gt_processed"], allow_pickle=True)
    if gt.shape == ():
        gt = gt.item()

    gt_hand = gt["cam_coord"][f"verts.{side}"][frame, view]
    gt_obj_mesh = make_gt_object_mesh(gt, frame, view)

    pred_hand_mesh = load_mesh(row["hand_mesh"])
    pred_obj_mesh = load_mesh(row["object_mesh"])

    pred_hand = np.asarray(pred_hand_mesh.vertices, dtype=np.float64)
    gt_hand = np.asarray(gt_hand, dtype=np.float64)

    n = min(len(pred_hand), len(gt_hand))
    scale, R, t = umeyama(pred_hand[:n], gt_hand[:n], with_scale=True)

    aligned_hand_vertices = apply_sim(pred_hand_mesh.vertices, scale, R, t)
    aligned_obj_vertices = apply_sim(pred_obj_mesh.vertices, scale, R, t)

    aligned_hand_mesh = trimesh.Trimesh(
        vertices=aligned_hand_vertices,
        faces=pred_hand_mesh.faces,
        process=False,
    )
    aligned_obj_mesh = trimesh.Trimesh(
        vertices=aligned_obj_vertices,
        faces=pred_obj_mesh.faces,
        process=False,
    )

    seed_base = abs(hash((case, method))) % (2**31 - 1)

    pred_obj_pts = sample_surface(aligned_obj_mesh, N_SAMPLES, seed_base)
    gt_obj_pts = sample_surface(gt_obj_mesh, N_SAMPLES, seed_base + 17)

    obj_m = cd_fscore(pred_obj_pts, gt_obj_pts)

    # Hand CD still uses vertices because MANO has correspondence.
    hand_m = cd_fscore(aligned_hand_vertices, gt_hand)

    case_dir = OUT_DIR / case / method
    case_dir.mkdir(parents=True, exist_ok=True)

    aligned_hand_mesh.export(case_dir / "aligned_pred_hand.ply")
    aligned_obj_mesh.export(case_dir / "aligned_pred_object.ply")
    gt_obj_mesh.export(case_dir / "gt_object_mesh.ply")
    trimesh.Trimesh(vertices=gt_hand, process=False).export(case_dir / f"gt_{side}_hand_points.ply")

    result = {
        "case": case,
        "method": method,
        "status": "ok",
        "fixed_gt_hand": side,
        "sim_scale": float(scale),
        "hand_cd_mm": hand_m["cd_m"] * 1000.0,
        "object_cd_mm": obj_m["cd_m"] * 1000.0,
        "object_pred_to_gt_mm": obj_m["pred_to_gt_m"] * 1000.0,
        "object_gt_to_pred_mm": obj_m["gt_to_pred_m"] * 1000.0,
        "object_f5": obj_m["fscore_5mm"],
        "object_f10": obj_m["fscore_10mm"],
        "object_precision_5mm": obj_m["precision_5mm"],
        "object_recall_5mm": obj_m["recall_5mm"],
        "object_precision_10mm": obj_m["precision_10mm"],
        "object_recall_10mm": obj_m["recall_10mm"],
        "n_surface_samples": N_SAMPLES,
        "hand_mesh": row["hand_mesh"],
        "object_mesh": row["object_mesh"],
    }

    rows.append(result)
    print(result)

df = pd.DataFrame(rows)
out_csv = OUT_DIR / "arctic_selected_cases_surface_paperstyle_metrics.csv"
df.to_csv(out_csv, index=False)

ok = df[df["status"] == "ok"].copy()
avg = ok.groupby("method")[[
    "hand_cd_mm",
    "object_cd_mm",
    "object_f5",
    "object_f10",
    "object_precision_5mm",
    "object_recall_5mm",
    "object_precision_10mm",
    "object_recall_10mm",
]].mean()

summary = OUT_DIR / "arctic_selected_cases_surface_paperstyle_summary.md"
summary.write_text(
    "# ARCTIC Selected Cases Surface-Sampled Paper-Style Metrics\n\n"
    "This is a selected-case paper-style evaluation over 5 manually selected Phase 0.17 ARCTIC cases.\n\n"
    "## Per-case metrics\n\n"
    + ok[[
        "case", "method", "fixed_gt_hand", "sim_scale", "hand_cd_mm",
        "object_cd_mm", "object_f5", "object_f10",
        "object_precision_5mm", "object_recall_5mm",
        "object_precision_10mm", "object_recall_10mm",
    ]].to_markdown(index=False)
    + "\n\n## Method averages\n\n"
    + avg.to_markdown()
    + "\n"
)

print("\n===== method averages =====")
print(avg.to_string())
print("[OK] wrote", out_csv)
print("[OK] wrote", summary)
