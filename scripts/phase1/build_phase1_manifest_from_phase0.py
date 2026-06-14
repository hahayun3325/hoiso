from pathlib import Path
import pickle
import numpy as np
import pandas as pd
import trimesh

HOME = Path.home()
REPO = Path("/home/fredcui/Projects/FollowMyHold")
PHASE0 = HOME / "foho_phase0"
PHASE1 = PHASE0 / "phase1_diagnostics"

OUT_MANIFEST = REPO / "data/phase1/manifests/phase1_samples.csv"
CACHE_T = PHASE1 / "cache_transforms"
CACHE_GT = PHASE1 / "cache_gt"

CACHE_T.mkdir(parents=True, exist_ok=True)
CACHE_GT.mkdir(parents=True, exist_ok=True)
OUT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

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
    return float(scale), R, t

def save_transform(path, scale, R, t, note):
    np.savez(path, scale=scale, sim_scale=scale, R=R, t=t, translation=t, note=note)

def export_points(path, vertices):
    pc = trimesh.PointCloud(np.asarray(vertices, dtype=np.float64))
    pc.export(path)

def make_arctic_gt_object_mesh(gt, frame, view):
    verts = np.asarray(gt["cam_coord"]["verts.object"][frame, view], dtype=np.float64)

    faces = np.asarray(gt["world_coord"]["f"][frame], dtype=np.int64)
    f_len = int(gt["world_coord"]["f_len"][frame])
    v_len = int(gt["world_coord"]["v_len"][frame])

    verts = verts[:v_len]
    faces = faces[:f_len]

    if faces.min() == 1 and faces.max() == v_len:
        faces = faces - 1

    valid = (faces >= 0).all(axis=1) & (faces < len(verts)).all(axis=1)
    faces = faces[valid]

    return trimesh.Trimesh(vertices=verts, faces=faces, process=False)

rows = []

# ---------------------------------------------------------------------
# ARCTIC: 5 cases x 2 methods
# ---------------------------------------------------------------------
arctic_manifest = PHASE0 / "inspection/arctic_phase017/paper_style_eval_selected_cases/arctic_selected_eval_mesh_manifest.csv"
side_map_csv = PHASE0 / "inspection/arctic_phase017/paper_style_eval_selected_cases/arctic_selected_case_hand_side_map.csv"

if arctic_manifest.exists() and side_map_csv.exists():
    arctic_df = pd.read_csv(arctic_manifest)
    side_df = pd.read_csv(side_map_csv)
    side_map = dict(zip(side_df["case"], side_df["chosen_gt_hand"]))

    for _, r in arctic_df.iterrows():
        case = r["case"]
        method = r["method"]
        frame = int(r["frame"])
        view = int(r["view_id"])
        side = side_map[case]

        sample_id = f"arctic_{case}_{method}"

        pred_hand_path = Path(r["hand_mesh"])
        pred_obj_path = Path(r["object_mesh"])
        gt_processed = Path(r["gt_processed"])

        gt = np.load(gt_processed, allow_pickle=True)
        if gt.shape == ():
            gt = gt.item()

        gt_hand = np.asarray(gt["cam_coord"][f"verts.{side}"][frame, view], dtype=np.float64)
        gt_obj_mesh = make_arctic_gt_object_mesh(gt, frame, view)

        gt_dir = CACHE_GT / sample_id
        gt_dir.mkdir(parents=True, exist_ok=True)

        gt_hand_path = gt_dir / "gt_hand_points.ply"
        gt_obj_path = gt_dir / "gt_object_mesh.ply"

        export_points(gt_hand_path, gt_hand)
        gt_obj_mesh.export(gt_obj_path)

        pred_hand = load_mesh(pred_hand_path)
        pred_hand_v = np.asarray(pred_hand.vertices, dtype=np.float64)

        n = min(len(pred_hand_v), len(gt_hand))
        scale, R, t = umeyama(pred_hand_v[:n], gt_hand[:n], with_scale=True)

        align_npz = CACHE_T / f"{sample_id}_hand_align.npz"
        save_transform(
            align_npz,
            scale,
            R,
            t,
            note=f"cached from Phase0 ARCTIC surface eval protocol; fixed_gt_hand={side}",
        )

        rows.append({
            "sample_id": sample_id,
            "dataset": "arctic",
            "case": case,
            "method": method,
            "phase0_run_id": Path(r["run_root"]).name,
            "input_image": "",
            "pred_hand_mesh": str(pred_hand_path),
            "pred_object_mesh": str(pred_obj_path),
            "gt_hand_mesh": str(gt_hand_path),
            "gt_object_mesh": str(gt_obj_path),
            "align_npz": str(align_npz),
            "gt_source": str(gt_processed),
            "frame": frame,
            "view_id": view,
            "fixed_gt_hand": side,
            "notes": "ARCTIC selected Phase0.17 case",
        })

# ---------------------------------------------------------------------
# OakInk split000: baseline + selector
# ---------------------------------------------------------------------
oak_csv = PHASE0 / "inspection/oakink_000/final_report_assets/oakink000_paper_like_metrics_mano_correspondence.csv"
oak_gt_dir = PHASE0 / "inspection/oakink_000/gt_assets"
oak_anno = oak_gt_dir / "oakink_image_annotation/selected_south_east_frame90"

if oak_csv.exists():
    oak_df = pd.read_csv(oak_csv)

    with open(oak_anno / "hand_v.pkl", "rb") as f:
        gt_hand = np.asarray(pickle.load(f), dtype=np.float64)

    with open(oak_anno / "obj_transf.pkl", "rb") as f:
        obj_T = np.asarray(pickle.load(f), dtype=np.float64)

    gt_obj_mesh = load_mesh(oak_gt_dir / "A01023.obj")
    gt_obj_mesh = gt_obj_mesh.copy()
    gt_obj_mesh.apply_transform(obj_T)

    for _, r in oak_df.iterrows():
        label = r["label"]
        method = "default" if label == "baseline" else "gpt55_selector"
        sample_id = f"oakink_split000_{method}"

        pred_hand_path = Path(r["pred_hand_path"])
        pred_obj_path = Path(r["pred_obj_path"])

        gt_dir = CACHE_GT / sample_id
        gt_dir.mkdir(parents=True, exist_ok=True)

        gt_hand_path = gt_dir / "gt_hand_points.ply"
        gt_obj_path = gt_dir / "gt_object_mesh.ply"

        export_points(gt_hand_path, gt_hand)
        gt_obj_mesh.export(gt_obj_path)

        pred_hand = load_mesh(pred_hand_path)
        pred_hand_v = np.asarray(pred_hand.vertices, dtype=np.float64)

        n = min(len(pred_hand_v), len(gt_hand))
        scale, R, t = umeyama(pred_hand_v[:n], gt_hand[:n], with_scale=True)

        align_npz = CACHE_T / f"{sample_id}_hand_align.npz"
        save_transform(
            align_npz,
            scale,
            R,
            t,
            note="cached from Phase0 OakInk MANO-correspondence protocol",
        )

        rows.append({
            "sample_id": sample_id,
            "dataset": "oakink",
            "case": "oakink_split000",
            "method": method,
            "phase0_run_id": r["run_id"],
            "input_image": "",
            "pred_hand_mesh": str(pred_hand_path),
            "pred_object_mesh": str(pred_obj_path),
            "gt_hand_mesh": str(gt_hand_path),
            "gt_object_mesh": str(gt_obj_path),
            "align_npz": str(align_npz),
            "gt_source": str(oak_gt_dir),
            "frame": "",
            "view_id": "south_east_color_90",
            "fixed_gt_hand": "mano_correspondence",
            "notes": "OakInk split000 Phase0 report case",
        })

out = pd.DataFrame(rows)
out.to_csv(OUT_MANIFEST, index=False)

print("[OK] wrote manifest:", OUT_MANIFEST)
print("[OK] rows:", len(out))
print(out[[
    "sample_id",
    "dataset",
    "method",
    "pred_hand_mesh",
    "pred_object_mesh",
    "gt_hand_mesh",
    "gt_object_mesh",
    "align_npz",
]].to_string(index=False))
