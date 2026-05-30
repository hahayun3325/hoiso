from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree


def load_mesh(path):
    path = Path(path)
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh


def sample_points(mesh, n=30000):
    pts, _ = trimesh.sample.sample_surface(mesh, n)
    return pts.astype(np.float64)


def chamfer_and_fscore(pred_pts, gt_pts, thresholds=(0.005, 0.01)):
    tree_gt = cKDTree(gt_pts)
    tree_pred = cKDTree(pred_pts)

    d_pred_to_gt, _ = tree_gt.query(pred_pts, k=1)
    d_gt_to_pred, _ = tree_pred.query(gt_pts, k=1)

    cd = float(np.mean(d_pred_to_gt ** 2) + np.mean(d_gt_to_pred ** 2))

    fscores = {}
    for th in thresholds:
        precision = float(np.mean(d_pred_to_gt < th))
        recall = float(np.mean(d_gt_to_pred < th))
        f = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
        fscores[f"F{int(th * 1000)}"] = f

    return cd, fscores


def mesh_fragmentation_score(mesh):
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest_ratio = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0.0

    return {
        "components": len(comps),
        "largest_face_ratio": float(largest_ratio),
        "fragmentation_score": float((len(comps) - 1) + (1.0 - largest_ratio)),
        "watertight": bool(mesh.is_watertight),
    }
