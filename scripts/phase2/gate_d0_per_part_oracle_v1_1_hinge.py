from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import trimesh
from scipy.spatial import cKDTree


def load_mesh(path: Path) -> trimesh.Trimesh:
    if not path.exists():
        raise FileNotFoundError(path)
    obj = trimesh.load(path, force=None, process=False)
    if isinstance(obj, trimesh.Scene):
        geoms = [g for g in obj.geometry.values() if hasattr(g, "vertices") and len(g.vertices) > 0]
        if not geoms:
            raise ValueError(f"empty scene: {path}")
        return trimesh.util.concatenate(geoms)
    if isinstance(obj, trimesh.Trimesh):
        if len(obj.vertices) == 0:
            raise ValueError(f"zero vertices: {path}")
        return obj
    raise TypeError(f"unsupported type {type(obj)} for {path}")


def sample_points(mesh: trimesh.Trimesh, n: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if hasattr(mesh, "faces") and len(mesh.faces) > 0:
        pts, _ = trimesh.sample.sample_surface(mesh, n)
        return np.asarray(pts, dtype=np.float64)
    verts = np.asarray(mesh.vertices, dtype=np.float64)
    if len(verts) <= n:
        return verts
    idx = rng.choice(len(verts), size=n, replace=False)
    return verts[idx]


def apply_T(points: np.ndarray, T: np.ndarray) -> np.ndarray:
    h = np.c_[points, np.ones(len(points))]
    return (T @ h.T).T[:, :3]


def rigid_delta(src_pts: np.ndarray, dst_pts: np.ndarray) -> np.ndarray:
    src_mean = src_pts.mean(axis=0)
    dst_mean = dst_pts.mean(axis=0)
    X = src_pts - src_mean
    Y = dst_pts - dst_mean
    H = X.T @ Y
    U, _, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = Vt.T @ U.T
    t = dst_mean - R @ src_mean
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def shared_scale_init(pred_union: trimesh.Trimesh, gt: trimesh.Trimesh) -> tuple[np.ndarray, float]:
    pred_extent = np.asarray(pred_union.bounds[1] - pred_union.bounds[0], dtype=np.float64)
    gt_extent = np.asarray(gt.bounds[1] - gt.bounds[0], dtype=np.float64)
    valid = pred_extent > 1e-9
    scale = float(np.median(gt_extent[valid] / pred_extent[valid]))

    pred_center = np.asarray(pred_union.centroid, dtype=np.float64)
    gt_center = np.asarray(gt.centroid, dtype=np.float64)

    T = np.eye(4)
    T[:3, :3] = np.eye(3) * scale
    T[:3, 3] = gt_center - scale * pred_center
    return T, scale


def icp_no_scale(src_mesh: trimesh.Trimesh, tgt_mesh: trimesh.Trimesh, T_init: np.ndarray, n_points: int, n_iters: int, seed: int) -> np.ndarray:
    src_sample = sample_points(src_mesh, n_points, seed=seed)
    tgt_sample = sample_points(tgt_mesh, n_points, seed=seed + 100)
    tree = cKDTree(tgt_sample)
    T = T_init.copy()

    for _ in range(n_iters):
        moved = apply_T(src_sample, T)
        d, idx = tree.query(moved, k=1)
        keep = d <= np.percentile(d, 85)
        if keep.sum() < 20:
            keep = np.ones_like(d, dtype=bool)
        delta = rigid_delta(moved[keep], tgt_sample[idx[keep]])
        T = delta @ T

    return T


def estimate_hinge_axis(base: trimesh.Trimesh, screen: trimesh.Trimesh, n_points: int = 8000) -> dict:
    base_pts = sample_points(base, n_points, seed=21)
    screen_pts = sample_points(screen, n_points, seed=22)

    tree = cKDTree(base_pts)
    d, idx = tree.query(screen_pts, k=1)

    # Hinge candidates are closest screen/base point pairs in the original predicted frame.
    keep = d <= np.percentile(d, 5)
    if keep.sum() < 20:
        keep = d <= np.percentile(d, 10)

    pair_mid = 0.5 * (screen_pts[keep] + base_pts[idx[keep]])
    center = pair_mid.mean(axis=0)

    X = pair_mid - center
    _, _, Vt = np.linalg.svd(X, full_matrices=False)
    axis = Vt[0]
    axis = axis / max(np.linalg.norm(axis), 1e-12)

    return {
        "center": center,
        "axis": axis,
        "num_pairs": int(keep.sum()),
        "mean_pair_distance": float(d[keep].mean()),
        "p95_pair_distance": float(np.percentile(d[keep], 95)),
    }


def rotation_about_axis(point: np.ndarray, axis: np.ndarray, angle_rad: float) -> np.ndarray:
    axis = axis / max(np.linalg.norm(axis), 1e-12)
    x, y, z = axis
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    C = 1 - c

    R = np.array([
        [c + x*x*C,     x*y*C - z*s, x*z*C + y*s],
        [y*x*C + z*s,   c + y*y*C,   y*z*C - x*s],
        [z*x*C - y*s,   z*y*C + x*s, c + z*z*C],
    ], dtype=np.float64)

    T1 = np.eye(4)
    T1[:3, 3] = -point

    T2 = np.eye(4)
    T2[:3, :3] = R

    T3 = np.eye(4)
    T3[:3, 3] = point

    return T3 @ T2 @ T1


def nn_dist(src: np.ndarray, tgt: np.ndarray) -> np.ndarray:
    tree = cKDTree(tgt)
    d, _ = tree.query(src, k=1)
    return d


def fscore(d_p2g: np.ndarray, d_g2p: np.ndarray, th: float) -> dict:
    precision = float((d_p2g <= th).mean())
    recall = float((d_g2p <= th).mean())
    if precision + recall <= 1e-12:
        f = 0.0
    else:
        f = float(2 * precision * recall / (precision + recall))
    return {"threshold": th, "precision_pred_to_gt": precision, "recall_gt_to_pred": recall, "fscore": f}


def bbox_stats(pred: trimesh.Trimesh, gt: trimesh.Trimesh) -> dict:
    pred_extent = np.asarray(pred.bounds[1] - pred.bounds[0], dtype=np.float64)
    gt_extent = np.asarray(gt.bounds[1] - gt.bounds[0], dtype=np.float64)
    eps = 1e-12
    axis_ratio = pred_extent / np.maximum(gt_extent, eps)
    pred_vol = float(np.prod(np.maximum(pred_extent, eps)))
    gt_vol = float(np.prod(np.maximum(gt_extent, eps)))
    return {
        "pred_extent_xyz": pred_extent.tolist(),
        "gt_extent_xyz": gt_extent.tolist(),
        "axis_ratio_pred_over_gt_xyz": axis_ratio.tolist(),
        "axis_ratio_min": float(axis_ratio.min()),
        "axis_ratio_max": float(axis_ratio.max()),
        "bbox_volume_ratio_pred_over_gt": pred_vol / max(gt_vol, eps),
        "centroid_error": float(np.linalg.norm(np.asarray(pred.centroid) - np.asarray(gt.centroid))),
    }


def eval_mesh_pair(name: str, pred: trimesh.Trimesh, gt: trimesh.Trimesh, n_points: int) -> dict:
    pred_pts = sample_points(pred, n_points, seed=31)
    gt_pts = sample_points(gt, n_points, seed=32)

    d_p2g = nn_dist(pred_pts, gt_pts)
    d_g2p = nn_dist(gt_pts, pred_pts)

    p2g = float(d_p2g.mean())
    g2p = float(d_g2p.mean())
    sym = 0.5 * (p2g + g2p)
    asym = g2p / max(p2g, 1e-12)

    bbox = bbox_stats(pred, gt)

    collapse_flags = {
        "bbox_volume_too_small": bbox["bbox_volume_ratio_pred_over_gt"] < 0.35,
        "bbox_volume_too_large": bbox["bbox_volume_ratio_pred_over_gt"] > 3.0,
        "bbox_axis_too_small": bbox["axis_ratio_min"] < 0.40,
        "bbox_axis_too_large": bbox["axis_ratio_max"] > 2.50,
        "gt_to_pred_too_large": g2p > 0.05,
        "asymmetric_distance_too_large": asym > 3.0,
    }

    collapse_flag = bool(any(collapse_flags.values()))

    return {
        "name": name,
        "pred_to_gt": {"mean": p2g, "median": float(np.median(d_p2g)), "p95": float(np.percentile(d_p2g, 95))},
        "gt_to_pred": {"mean": g2p, "median": float(np.median(d_g2p)), "p95": float(np.percentile(d_g2p, 95))},
        "symmetric_mean": sym,
        "asymmetry_ratio": float(asym),
        "fscore": {
            "f5mm": fscore(d_p2g, d_g2p, 0.005),
            "f10mm": fscore(d_p2g, d_g2p, 0.010),
            "f30mm": fscore(d_p2g, d_g2p, 0.030),
            "f50mm": fscore(d_p2g, d_g2p, 0.050),
        },
        "bbox": bbox,
        "collapse_flags": collapse_flags,
        "collapse_flag": collapse_flag,
        "diagnostic_decision": "REJECT_AS_COLLAPSED_OR_UNRELIABLE" if collapse_flag else "NO_COLLAPSE_FLAG",
    }


def colorize(mesh: trimesh.Trimesh, rgba: list[int]) -> trimesh.Trimesh:
    out = mesh.copy()
    out.visual.vertex_colors = rgba
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-root", required=True)
    ap.add_argument("--n-points", type=int, default=20000)
    ap.add_argument("--iters", type=int, default=30)
    ap.add_argument("--angle-min", type=float, default=-120.0)
    ap.add_argument("--angle-max", type=float, default=120.0)
    ap.add_argument("--angle-step", type=float, default=5.0)
    args = ap.parse_args()

    case_root = Path(args.case_root)
    part_dir = case_root / "part_meshes_partfield_v2_vmap"
    out_root = case_root / "gate_d0_object_repair/per_part_oracle_v1_1_hinge"
    out_mesh = out_root / "outputs"
    out_vis = out_root / "visuals"
    out_metrics = out_root / "metrics"
    out_notes = out_root / "notes"
    for p in [out_mesh, out_vis, out_metrics, out_notes]:
        p.mkdir(parents=True, exist_ok=True)

    screen = load_mesh(part_dir / "screen.ply")
    base = load_mesh(part_dir / "keyboard_base.ply")
    gt = load_mesh(case_root / "gt_reference/selected/gt_object_mesh.ply")

    hinge_path = part_dir / "hinge.ply"
    hinge = load_mesh(hinge_path) if hinge_path.exists() else None

    pred_union = trimesh.util.concatenate([base, screen] + ([hinge] if hinge is not None else []))
    T0, shared_scale = shared_scale_init(pred_union, gt)

    # Root pose: fit keyboard_base only. This keeps base as root.
    T_base = icp_no_scale(base, gt, T0, args.n_points, args.iters, seed=41)

    hinge_info = estimate_hinge_axis(base, screen)
    center = hinge_info["center"]
    axis = hinge_info["axis"]

    best = None
    angle_values = np.arange(args.angle_min, args.angle_max + 1e-6, args.angle_step)

    base_moved = base.copy()
    base_moved.apply_transform(T_base)

    hinge_moved = None
    if hinge is not None:
        hinge_moved = hinge.copy()
        hinge_moved.apply_transform(T_base)

    for angle_deg in angle_values:
        A = rotation_about_axis(center, axis, math.radians(float(angle_deg)))

        # Connected hinge model:
        # screen cannot independently translate.
        # screen moves only by rotation around the hinge in original object frame, then follows base root transform.
        T_screen = T_base @ A

        screen_moved = screen.copy()
        screen_moved.apply_transform(T_screen)

        parts = [base_moved, screen_moved]
        if hinge_moved is not None:
            parts.append(hinge_moved)

        union = trimesh.util.concatenate(parts)
        metrics = eval_mesh_pair(f"hinge_angle_{angle_deg:.1f}", union, gt, args.n_points)

        score = (
            metrics["symmetric_mean"]
            + 0.05 * abs(metrics["bbox"]["bbox_volume_ratio_pred_over_gt"] - 1.0)
            + (10.0 if metrics["collapse_flag"] else 0.0)
        )

        if best is None or score < best["score"]:
            best = {
                "angle_deg": float(angle_deg),
                "score": float(score),
                "metrics": metrics,
                "T_screen": T_screen,
                "screen_moved": screen_moved,
                "union": union,
            }

    assert best is not None

    best_angle = best["angle_deg"]
    best_screen = best["screen_moved"]
    best_union = best["union"]
    best_metrics = best["metrics"]

    base_moved.export(out_mesh / "keyboard_base_hinge_v1_1.ply")
    best_screen.export(out_mesh / "screen_hinge_v1_1.ply")
    best_union.export(out_mesh / "object_hinge_v1_1_union.ply")
    if hinge_moved is not None:
        hinge_moved.export(out_mesh / "hinge_hinge_v1_1.ply")

    # Hinge connection proxy after movement
    s_pts = sample_points(best_screen, 8000, seed=51)
    b_pts = sample_points(base_moved, 8000, seed=52)
    d, _ = cKDTree(b_pts).query(s_pts, k=1)
    hinge_gap = {
        "screen_to_base_nn_min": float(d.min()),
        "screen_to_base_nn_p1": float(np.percentile(d, 1)),
        "screen_to_base_nn_p5": float(np.percentile(d, 5)),
        "screen_to_base_nn_mean": float(d.mean()),
    }

    if best_metrics["collapse_flag"]:
        overall = "HINGE_ORACLE_V1_1_REJECTED_BY_COLLAPSE_GUARD"
    elif hinge_gap["screen_to_base_nn_p5"] > 0.03:
        overall = "HINGE_ORACLE_V1_1_NEEDS_HINGE_AXIS_REFINEMENT"
    else:
        overall = "HINGE_ORACLE_V1_1_NO_COLLAPSE_VISUAL_CHECK_REQUIRED"

    result = {
        "case_id": case_root.name,
        "stage": "Gate D-0 per-part oracle v1.1 connected hinge",
        "purpose": "test shared-scale base-root + screen hinge-angle model",
        "important_constraints": [
            "one shared global scale",
            "keyboard_base is root",
            "screen has no independent translation",
            "screen moves only by rotation around estimated hinge axis",
            "no independent per-part scale"
        ],
        "shared_scale": shared_scale,
        "estimated_hinge_axis_original_frame": {
            "center": center.tolist(),
            "axis": axis.tolist(),
            "num_pairs": hinge_info["num_pairs"],
            "mean_pair_distance": hinge_info["mean_pair_distance"],
            "p95_pair_distance": hinge_info["p95_pair_distance"],
        },
        "angle_grid": {
            "min": args.angle_min,
            "max": args.angle_max,
            "step": args.angle_step,
        },
        "best_angle_deg": best_angle,
        "best_score": best["score"],
        "whole_metrics": best_metrics,
        "hinge_gap_proxy": hinge_gap,
        "overall_decision": overall,
        "warnings": [
            "This is an oracle diagnostic, not a final non-GT method.",
            "GT whole object is still used as the scoring target.",
            "Hinge axis is estimated from predicted screen/base nearest boundary; inspect visually.",
            "If this fails, refine Gate A parts or hinge-axis estimation."
        ],
    }

    out_json = out_metrics / "gate_d0_per_part_oracle_v1_1_hinge_metrics.json"
    out_json.write_text(json.dumps(result, indent=2))

    scene = trimesh.Scene()
    scene.add_geometry(colorize(gt, [180, 180, 180, 90]), node_name="gt_object_gray")
    scene.add_geometry(colorize(base_moved, [255, 140, 0, 190]), node_name="keyboard_base_root_orange")
    scene.add_geometry(colorize(best_screen, [0, 0, 255, 180]), node_name="screen_hinged_blue")
    if hinge_moved is not None:
        scene.add_geometry(colorize(hinge_moved, [255, 0, 255, 220]), node_name="hinge_root_magenta")
    scene.export(out_vis / "gate_d0_per_part_oracle_v1_1_hinge_scene.glb")

    print("[OK] wrote", out_json)
    print("[OK] wrote", out_vis / "gate_d0_per_part_oracle_v1_1_hinge_scene.glb")
    print("[DECISION]", overall)
    print("[shared_scale]", shared_scale)
    print("[best_angle_deg]", best_angle)
    print("[collapse]", best_metrics["collapse_flag"])
    print("[pred_to_gt_mean]", best_metrics["pred_to_gt"]["mean"])
    print("[gt_to_pred_mean]", best_metrics["gt_to_pred"]["mean"])
    print("[symmetric_mean]", best_metrics["symmetric_mean"])
    print("[bbox_volume_ratio]", best_metrics["bbox"]["bbox_volume_ratio_pred_over_gt"])
    print("[hinge_gap_p5]", hinge_gap["screen_to_base_nn_p5"])


if __name__ == "__main__":
    main()
