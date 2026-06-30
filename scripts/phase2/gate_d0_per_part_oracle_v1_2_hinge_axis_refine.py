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
        geoms = [
            g for g in obj.geometry.values()
            if hasattr(g, "vertices") and len(g.vertices) > 0
        ]
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


def icp_no_scale_to_points(
    src_mesh: trimesh.Trimesh,
    tgt_pts: np.ndarray,
    T_init: np.ndarray,
    n_points: int,
    n_iters: int,
    seed: int,
) -> np.ndarray:
    src_sample = sample_points(src_mesh, n_points, seed=seed)
    tree = cKDTree(tgt_pts)
    T = T_init.copy()

    for _ in range(n_iters):
        moved = apply_T(src_sample, T)
        d, idx = tree.query(moved, k=1)

        keep = d <= np.percentile(d, 85)
        if keep.sum() < 20:
            keep = np.ones_like(d, dtype=bool)

        delta = rigid_delta(moved[keep], tgt_pts[idx[keep]])
        T = delta @ T

    return T


def pca_axes(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    center = points.mean(axis=0)
    X = points - center
    _, _, Vt = np.linalg.svd(X, full_matrices=False)
    return center, Vt


def kmeans2(points: np.ndarray, n_iters: int = 30) -> tuple[np.ndarray, np.ndarray]:
    center, axes = pca_axes(points)
    proj = (points - center) @ axes[0]

    c0 = points[proj <= np.median(proj)].mean(axis=0)
    c1 = points[proj > np.median(proj)].mean(axis=0)
    centers = np.stack([c0, c1], axis=0)

    for _ in range(n_iters):
        d = np.linalg.norm(points[:, None, :] - centers[None, :, :], axis=2)
        labels = d.argmin(axis=1)

        new_centers = []
        for k in range(2):
            if np.any(labels == k):
                new_centers.append(points[labels == k].mean(axis=0))
            else:
                new_centers.append(centers[k])
        centers = np.stack(new_centers, axis=0)

    d = np.linalg.norm(points[:, None, :] - centers[None, :, :], axis=2)
    labels = d.argmin(axis=1)
    return labels, centers


def rotation_about_axis(point: np.ndarray, axis: np.ndarray, angle_rad: float) -> np.ndarray:
    axis = axis / max(np.linalg.norm(axis), 1e-12)

    x, y, z = axis
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    C = 1.0 - c

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


def estimate_boundary_hinge(base: trimesh.Trimesh, screen: trimesh.Trimesh, n_points: int = 10000) -> dict:
    base_pts = sample_points(base, n_points, seed=11)
    screen_pts = sample_points(screen, n_points, seed=12)

    tree = cKDTree(base_pts)
    d, idx = tree.query(screen_pts, k=1)

    keep = d <= np.percentile(d, 5)
    if keep.sum() < 30:
        keep = d <= np.percentile(d, 10)

    pair_mid = 0.5 * (screen_pts[keep] + base_pts[idx[keep]])
    center, axes = pca_axes(pair_mid)

    axis = axes[0]
    axis = axis / max(np.linalg.norm(axis), 1e-12)

    return {
        "center": center,
        "axis": axis,
        "axes": axes,
        "pair_mid": pair_mid,
        "num_pairs": int(keep.sum()),
        "mean_pair_distance": float(d[keep].mean()),
        "p95_pair_distance": float(np.percentile(d[keep], 95)),
    }


def make_axis_candidates(boundary_info: dict, base: trimesh.Trimesh, screen: trimesh.Trimesh) -> list[dict]:
    candidates = []

    def add(name: str, axis: np.ndarray):
        axis = axis / max(np.linalg.norm(axis), 1e-12)
        candidates.append({"name": name, "axis": axis})
        candidates.append({"name": name + "_neg", "axis": -axis})

    add("boundary_pca_axis", boundary_info["axis"])

    base_pts = sample_points(base, 8000, seed=21)
    screen_pts = sample_points(screen, 8000, seed=22)
    _, base_axes = pca_axes(base_pts)
    _, screen_axes = pca_axes(screen_pts)

    add("base_pca_axis_0", base_axes[0])
    add("base_pca_axis_1", base_axes[1])
    add("screen_pca_axis_0", screen_axes[0])
    add("screen_pca_axis_1", screen_axes[1])

    # Deduplicate near-identical axes up to sign.
    unique = []
    for c in candidates:
        keep = True
        for u in unique:
            if abs(float(np.dot(c["axis"], u["axis"]))) > 0.97:
                keep = False
                break
        if keep:
            unique.append(c)

    return unique


def make_center_candidates(boundary_info: dict, scale: float = 1.0) -> list[dict]:
    center = boundary_info["center"]
    axes = boundary_info["axes"]

    # Offsets in original predicted frame.
    # Small offsets help recover a weak hinge center estimate.
    step = 0.03 / max(scale, 1e-6)
    offsets = [0.0, -step, step, -2 * step, 2 * step]

    cands = []
    for i, ax in enumerate(axes[:3]):
        ax = ax / max(np.linalg.norm(ax), 1e-12)
        for off in offsets:
            cands.append({
                "name": f"pca{i}_offset_{off:.4f}",
                "center": center + off * ax,
            })

    cands.append({"name": "boundary_center", "center": center})

    # Deduplicate very close centers.
    unique = []
    for c in cands:
        if not any(np.linalg.norm(c["center"] - u["center"]) < 1e-6 for u in unique):
            unique.append(c)

    return unique


def nn_dist(src: np.ndarray, tgt: np.ndarray) -> np.ndarray:
    tree = cKDTree(tgt)
    d, _ = tree.query(src, k=1)
    return d


def symmetric_point_distance(src_pts: np.ndarray, tgt_pts: np.ndarray) -> dict:
    d1 = nn_dist(src_pts, tgt_pts)
    d2 = nn_dist(tgt_pts, src_pts)
    return {
        "src_to_tgt_mean": float(d1.mean()),
        "tgt_to_src_mean": float(d2.mean()),
        "symmetric_mean": float(0.5 * (d1.mean() + d2.mean())),
    }


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
    sym = float(0.5 * (p2g + g2p))
    asym = float(g2p / max(p2g, 1e-12))

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
        "pred_to_gt": {
            "mean": p2g,
            "median": float(np.median(d_p2g)),
            "p95": float(np.percentile(d_p2g, 95)),
        },
        "gt_to_pred": {
            "mean": g2p,
            "median": float(np.median(d_g2p)),
            "p95": float(np.percentile(d_g2p, 95)),
        },
        "symmetric_mean": sym,
        "asymmetry_ratio": asym,
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
    ap.add_argument("--top-k", type=int, default=10)
    args = ap.parse_args()

    case_root = Path(args.case_root)
    part_dir = case_root / "part_meshes_partfield_v2_vmap"

    out_root = case_root / "gate_d0_object_repair/per_part_oracle_v1_2_hinge_axis_refine"
    out_mesh = out_root / "outputs"
    out_vis = out_root / "visuals"
    out_metrics = out_root / "metrics"
    for p in [out_mesh, out_vis, out_metrics]:
        p.mkdir(parents=True, exist_ok=True)

    screen = load_mesh(part_dir / "screen.ply")
    base = load_mesh(part_dir / "keyboard_base.ply")
    hinge_path = part_dir / "hinge.ply"
    hinge = load_mesh(hinge_path) if hinge_path.exists() else None
    gt = load_mesh(case_root / "gt_reference/selected/gt_object_mesh.ply")

    pred_union = trimesh.util.concatenate([base, screen] + ([hinge] if hinge is not None else []))
    T0, shared_scale = shared_scale_init(pred_union, gt)

    gt_pts = sample_points(gt, args.n_points, seed=100)
    labels, centers = kmeans2(gt_pts, n_iters=40)
    gt_clusters = [gt_pts[labels == 0], gt_pts[labels == 1]]

    # Boundary / hinge candidates in original predicted frame.
    boundary = estimate_boundary_hinge(base, screen)
    axis_candidates = make_axis_candidates(boundary, base, screen)
    center_candidates = make_center_candidates(boundary, scale=shared_scale)

    angle_values = np.arange(args.angle_min, args.angle_max + 1e-6, args.angle_step)

    all_candidates = []

    # Try both GT clusters as possible base target.
    for base_cluster_idx in [0, 1]:
        screen_cluster_idx = 1 - base_cluster_idx

        base_target = gt_clusters[base_cluster_idx]
        screen_target = gt_clusters[screen_cluster_idx]

        T_base = icp_no_scale_to_points(
            src_mesh=base,
            tgt_pts=base_target,
            T_init=T0,
            n_points=args.n_points,
            n_iters=args.iters,
            seed=200 + base_cluster_idx,
        )

        base_moved = base.copy()
        base_moved.apply_transform(T_base)

        hinge_moved = None
        if hinge is not None:
            hinge_moved = hinge.copy()
            hinge_moved.apply_transform(T_base)

        base_eval_pts = sample_points(base_moved, max(5000, args.n_points // 2), seed=301)
        base_part_score = symmetric_point_distance(base_eval_pts, base_target)["symmetric_mean"]

        for axis_c in axis_candidates:
            for center_c in center_candidates:
                axis = axis_c["axis"]
                center = center_c["center"]

                for angle_deg in angle_values:
                    A = rotation_about_axis(center, axis, math.radians(float(angle_deg)))
                    T_screen = T_base @ A

                    screen_moved = screen.copy()
                    screen_moved.apply_transform(T_screen)

                    parts = [base_moved, screen_moved]
                    if hinge_moved is not None:
                        parts.append(hinge_moved)

                    union = trimesh.util.concatenate(parts)
                    whole_metrics = eval_mesh_pair(
                        f"basecluster{base_cluster_idx}_{axis_c['name']}_{center_c['name']}_angle{angle_deg:.1f}",
                        union,
                        gt,
                        args.n_points,
                    )

                    screen_eval_pts = sample_points(screen_moved, max(5000, args.n_points // 2), seed=302)
                    screen_part_score = symmetric_point_distance(screen_eval_pts, screen_target)["symmetric_mean"]

                    s_pts = sample_points(screen_moved, 6000, seed=401)
                    b_pts = sample_points(base_moved, 6000, seed=402)
                    d, _ = cKDTree(b_pts).query(s_pts, k=1)
                    hinge_gap_p5 = float(np.percentile(d, 5))

                    bbox_volume = whole_metrics["bbox"]["bbox_volume_ratio_pred_over_gt"]

                    score = (
                        whole_metrics["symmetric_mean"]
                        + 0.35 * base_part_score
                        + 0.35 * screen_part_score
                        + 0.05 * abs(bbox_volume - 1.0)
                        + 0.50 * max(0.0, hinge_gap_p5 - 0.015)
                        + (10.0 if whole_metrics["collapse_flag"] else 0.0)
                    )

                    all_candidates.append({
                        "score": float(score),
                        "base_cluster_idx": int(base_cluster_idx),
                        "screen_cluster_idx": int(screen_cluster_idx),
                        "axis_name": axis_c["name"],
                        "center_name": center_c["name"],
                        "angle_deg": float(angle_deg),
                        "base_part_score": float(base_part_score),
                        "screen_part_score": float(screen_part_score),
                        "hinge_gap_p5": hinge_gap_p5,
                        "whole_symmetric_mean": whole_metrics["symmetric_mean"],
                        "bbox_volume_ratio": bbox_volume,
                        "collapse_flag": whole_metrics["collapse_flag"],
                        "T_base": T_base,
                        "T_screen": T_screen,
                        "base_moved": base_moved,
                        "screen_moved": screen_moved,
                        "hinge_moved": hinge_moved,
                        "union": union,
                        "whole_metrics": whole_metrics,
                    })

    all_candidates = sorted(all_candidates, key=lambda x: x["score"])
    best = all_candidates[0]

    best["base_moved"].export(out_mesh / "keyboard_base_hinge_v1_2.ply")
    best["screen_moved"].export(out_mesh / "screen_hinge_v1_2.ply")
    best["union"].export(out_mesh / "object_hinge_v1_2_union.ply")
    if best["hinge_moved"] is not None:
        best["hinge_moved"].export(out_mesh / "hinge_hinge_v1_2.ply")

    if best["whole_metrics"]["collapse_flag"]:
        overall = "HINGE_ORACLE_V1_2_REJECTED_BY_COLLAPSE_GUARD"
    elif best["hinge_gap_p5"] > 0.03:
        overall = "HINGE_ORACLE_V1_2_NEEDS_HINGE_CONNECTIVITY_REFINEMENT"
    else:
        overall = "HINGE_ORACLE_V1_2_NO_COLLAPSE_VISUAL_CHECK_REQUIRED"

    top = []
    for c in all_candidates[:args.top_k]:
        top.append({
            "score": c["score"],
            "base_cluster_idx": c["base_cluster_idx"],
            "screen_cluster_idx": c["screen_cluster_idx"],
            "axis_name": c["axis_name"],
            "center_name": c["center_name"],
            "angle_deg": c["angle_deg"],
            "base_part_score": c["base_part_score"],
            "screen_part_score": c["screen_part_score"],
            "hinge_gap_p5": c["hinge_gap_p5"],
            "whole_symmetric_mean": c["whole_symmetric_mean"],
            "bbox_volume_ratio": c["bbox_volume_ratio"],
            "collapse_flag": c["collapse_flag"],
        })

    result = {
        "case_id": case_root.name,
        "stage": "Gate D-0 per-part oracle v1.2 hinge-axis refinement",
        "purpose": "refine hinge axis/center and use pseudo part-aware GT scoring",
        "shared_scale": shared_scale,
        "search_space": {
            "num_axis_candidates": len(axis_candidates),
            "num_center_candidates": len(center_candidates),
            "num_angle_values": len(angle_values),
            "num_total_candidates": len(all_candidates),
            "angle_min": args.angle_min,
            "angle_max": args.angle_max,
            "angle_step": args.angle_step,
        },
        "estimated_boundary_hinge": {
            "center": boundary["center"].tolist(),
            "axis": boundary["axis"].tolist(),
            "num_pairs": boundary["num_pairs"],
            "mean_pair_distance": boundary["mean_pair_distance"],
            "p95_pair_distance": boundary["p95_pair_distance"],
        },
        "best": {
            "score": best["score"],
            "base_cluster_idx": best["base_cluster_idx"],
            "screen_cluster_idx": best["screen_cluster_idx"],
            "axis_name": best["axis_name"],
            "center_name": best["center_name"],
            "angle_deg": best["angle_deg"],
            "base_part_score": best["base_part_score"],
            "screen_part_score": best["screen_part_score"],
            "hinge_gap_p5": best["hinge_gap_p5"],
            "T_base": best["T_base"].tolist(),
            "T_screen": best["T_screen"].tolist(),
        },
        "whole_metrics": best["whole_metrics"],
        "top_candidates": top,
        "overall_decision": overall,
        "warnings": [
            "This is still an oracle diagnostic, not a final method.",
            "GT is used for scoring, but pseudo screen/base split is unsupervised.",
            "Visual inspection is required before Gate C v3.",
            "If v1.2 still misaligns visually, inspect Gate A part quality and pseudo-GT split."
        ],
    }

    out_json = out_metrics / "gate_d0_per_part_oracle_v1_2_hinge_axis_refine_metrics.json"
    out_json.write_text(json.dumps(result, indent=2))

    scene = trimesh.Scene()
    scene.add_geometry(colorize(gt, [180, 180, 180, 80]), node_name="gt_object_gray")
    scene.add_geometry(colorize(best["base_moved"], [255, 140, 0, 190]), node_name="keyboard_base_root_orange")
    scene.add_geometry(colorize(best["screen_moved"], [0, 0, 255, 180]), node_name="screen_hinged_blue")
    if best["hinge_moved"] is not None:
        scene.add_geometry(colorize(best["hinge_moved"], [255, 0, 255, 220]), node_name="hinge_root_magenta")
    scene.export(out_root / "visuals/gate_d0_per_part_oracle_v1_2_hinge_axis_refine_scene.glb")

    print("[OK] wrote", out_json)
    print("[OK] wrote", out_root / "visuals/gate_d0_per_part_oracle_v1_2_hinge_axis_refine_scene.glb")
    print("[DECISION]", overall)
    print("[shared_scale]", shared_scale)
    print("[best_angle_deg]", best["angle_deg"])
    print("[best_axis]", best["axis_name"])
    print("[best_center]", best["center_name"])
    print("[best_base_cluster]", best["base_cluster_idx"])
    print("[collapse]", best["whole_metrics"]["collapse_flag"])
    print("[pred_to_gt_mean]", best["whole_metrics"]["pred_to_gt"]["mean"])
    print("[gt_to_pred_mean]", best["whole_metrics"]["gt_to_pred"]["mean"])
    print("[symmetric_mean]", best["whole_metrics"]["symmetric_mean"])
    print("[bbox_volume_ratio]", best["whole_metrics"]["bbox"]["bbox_volume_ratio_pred_over_gt"])
    print("[hinge_gap_p5]", best["hinge_gap_p5"])
    print("[searched_candidates]", len(all_candidates))


if __name__ == "__main__":
    main()
