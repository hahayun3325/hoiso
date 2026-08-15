from __future__ import annotations

import argparse
import json
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
        mesh = trimesh.util.concatenate(geoms)
    elif isinstance(obj, trimesh.Trimesh):
        mesh = obj
    else:
        raise TypeError(f"unsupported geometry type: {type(obj)}")

    if len(mesh.vertices) == 0:
        raise ValueError(f"zero vertices: {path}")

    return mesh


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


def make_shared_scale_init(pred_union: trimesh.Trimesh, gt: trimesh.Trimesh) -> tuple[np.ndarray, float]:
    pred_extent = np.asarray(pred_union.bounds[1] - pred_union.bounds[0], dtype=np.float64)
    gt_extent = np.asarray(gt.bounds[1] - gt.bounds[0], dtype=np.float64)

    valid = pred_extent > 1e-9
    ratios = gt_extent[valid] / pred_extent[valid]
    shared_scale = float(np.median(ratios))

    pred_center = np.asarray(pred_union.centroid, dtype=np.float64)
    gt_center = np.asarray(gt.centroid, dtype=np.float64)

    T = np.eye(4)
    T[:3, :3] = np.eye(3) * shared_scale
    T[:3, 3] = gt_center - shared_scale * pred_center

    return T, shared_scale


def icp_no_scale(
    src_mesh: trimesh.Trimesh,
    tgt_mesh: trimesh.Trimesh,
    T_init: np.ndarray,
    n_points: int,
    n_iters: int,
    seed: int,
    trim_percentile: float = 85.0,
) -> np.ndarray:
    src_sample = sample_points(src_mesh, n_points, seed=seed)
    tgt_sample = sample_points(tgt_mesh, n_points, seed=seed + 100)

    tree = cKDTree(tgt_sample)
    T = T_init.copy()

    for _ in range(n_iters):
        moved = apply_T(src_sample, T)
        d, idx = tree.query(moved, k=1)

        keep = d <= np.percentile(d, trim_percentile)
        if keep.sum() < 20:
            keep = np.ones_like(d, dtype=bool)

        delta = rigid_delta(moved[keep], tgt_sample[idx[keep]])
        T = delta @ T

    return T


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
        f = float(2.0 * precision * recall / (precision + recall))
    return {
        "threshold": th,
        "precision_pred_to_gt": precision,
        "recall_gt_to_pred": recall,
        "fscore": f,
    }


def bbox_stats(pred: trimesh.Trimesh, gt: trimesh.Trimesh) -> dict:
    pred_extent = np.asarray(pred.bounds[1] - pred.bounds[0], dtype=np.float64)
    gt_extent = np.asarray(gt.bounds[1] - gt.bounds[0], dtype=np.float64)

    eps = 1e-12
    axis_ratio = pred_extent / np.maximum(gt_extent, eps)

    pred_vol = float(np.prod(np.maximum(pred_extent, eps)))
    gt_vol = float(np.prod(np.maximum(gt_extent, eps)))

    centroid_error = float(np.linalg.norm(np.asarray(pred.centroid) - np.asarray(gt.centroid)))

    return {
        "pred_extent_xyz": pred_extent.tolist(),
        "gt_extent_xyz": gt_extent.tolist(),
        "axis_ratio_pred_over_gt_xyz": axis_ratio.tolist(),
        "axis_ratio_min": float(axis_ratio.min()),
        "axis_ratio_max": float(axis_ratio.max()),
        "bbox_volume_ratio_pred_over_gt": pred_vol / max(gt_vol, eps),
        "centroid_error": centroid_error,
    }


def eval_mesh_pair(name: str, pred: trimesh.Trimesh, gt: trimesh.Trimesh, n_points: int) -> dict:
    pred_pts = sample_points(pred, n_points, seed=10)
    gt_pts = sample_points(gt, n_points, seed=11)

    d_p2g = nn_dist(pred_pts, gt_pts)
    d_g2p = nn_dist(gt_pts, pred_pts)

    pred_to_gt_mean = float(d_p2g.mean())
    gt_to_pred_mean = float(d_g2p.mean())
    symmetric_mean = float(0.5 * (pred_to_gt_mean + gt_to_pred_mean))
    asymmetry_ratio = float(gt_to_pred_mean / max(pred_to_gt_mean, 1e-12))

    bbox = bbox_stats(pred, gt)

    collapse_flags = {
        "bbox_volume_too_small": bbox["bbox_volume_ratio_pred_over_gt"] < 0.35,
        "bbox_volume_too_large": bbox["bbox_volume_ratio_pred_over_gt"] > 3.0,
        "bbox_axis_too_small": bbox["axis_ratio_min"] < 0.40,
        "bbox_axis_too_large": bbox["axis_ratio_max"] > 2.50,
        "gt_to_pred_too_large": gt_to_pred_mean > 0.05,
        "asymmetric_distance_too_large": asymmetry_ratio > 3.0,
    }

    collapse_flag = bool(any(collapse_flags.values()))

    return {
        "name": name,
        "pred_to_gt": {
            "mean": pred_to_gt_mean,
            "median": float(np.median(d_p2g)),
            "p95": float(np.percentile(d_p2g, 95)),
        },
        "gt_to_pred": {
            "mean": gt_to_pred_mean,
            "median": float(np.median(d_g2p)),
            "p95": float(np.percentile(d_g2p, 95)),
        },
        "symmetric_mean": symmetric_mean,
        "asymmetry_ratio": asymmetry_ratio,
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
    args = ap.parse_args()

    case_root = Path(args.case_root)

    part_dir = case_root / "part_meshes_partfield_v2_vmap"
    gt_object_path = case_root / "gt_reference/selected/gt_object_mesh.ply"
    gt_parts_dir = case_root / "gt_reference/selected/gt_parts"

    out_root = case_root / "gate_d0_object_repair/per_part_oracle_v1"
    out_mesh = out_root / "outputs"
    out_vis = out_root / "visuals"
    out_metrics = out_root / "metrics"
    out_mesh.mkdir(parents=True, exist_ok=True)
    out_vis.mkdir(parents=True, exist_ok=True)
    out_metrics.mkdir(parents=True, exist_ok=True)

    pred_part_paths = {
        "screen": part_dir / "screen.ply",
        "keyboard_base": part_dir / "keyboard_base.ply",
        "hinge": part_dir / "hinge.ply",
    }

    pred_parts = {}
    for name, path in pred_part_paths.items():
        if path.exists():
            pred_parts[name] = load_mesh(path)

    required = ["screen", "keyboard_base"]
    missing = [x for x in required if x not in pred_parts]
    if missing:
        raise FileNotFoundError(f"missing required predicted parts: {missing}")

    gt_object = load_mesh(gt_object_path)

    pred_union = trimesh.util.concatenate(list(pred_parts.values()))
    T0, shared_scale = make_shared_scale_init(pred_union, gt_object)

    transformed_parts = {}
    transforms = {}
    target_mode = {}

    for name, mesh in pred_parts.items():
        gt_part_path = gt_parts_dir / f"{name}.ply"
        if gt_part_path.exists():
            target = load_mesh(gt_part_path)
            target_mode[name] = f"gt_part:{gt_part_path}"
        else:
            target = gt_object
            target_mode[name] = "whole_gt_proxy_no_gt_part_label"

        T_part = icp_no_scale(
            src_mesh=mesh,
            tgt_mesh=target,
            T_init=T0,
            n_points=args.n_points,
            n_iters=args.iters,
            seed=100 + len(name),
        )

        moved = mesh.copy()
        moved.apply_transform(T_part)

        transformed_parts[name] = moved
        transforms[name] = T_part.tolist()
        moved.export(out_mesh / f"{name}_per_part_oracle_v1.ply")

    repaired_union = trimesh.util.concatenate(list(transformed_parts.values()))
    repaired_union.export(out_mesh / "object_per_part_oracle_v1_union.ply")

    whole_metrics = eval_mesh_pair(
        "per_part_oracle_v1_union_to_gt_object",
        repaired_union,
        gt_object,
        args.n_points,
    )

    part_metrics = {}
    for name, mesh in transformed_parts.items():
        gt_part_path = gt_parts_dir / f"{name}.ply"
        target = load_mesh(gt_part_path) if gt_part_path.exists() else gt_object
        part_metrics[name] = eval_mesh_pair(
            f"{name}_to_{'gt_part' if gt_part_path.exists() else 'gt_object_proxy'}",
            mesh,
            target,
            max(5000, args.n_points // 2),
        )

    hinge_gap = None
    if "screen" in transformed_parts and "keyboard_base" in transformed_parts:
        s_pts = sample_points(transformed_parts["screen"], 8000, seed=201)
        b_pts = sample_points(transformed_parts["keyboard_base"], 8000, seed=202)
        d, _ = cKDTree(b_pts).query(s_pts, k=1)
        hinge_gap = {
            "screen_to_base_nn_min": float(d.min()),
            "screen_to_base_nn_p1": float(np.percentile(d, 1)),
            "screen_to_base_nn_p5": float(np.percentile(d, 5)),
            "screen_to_base_nn_mean": float(d.mean()),
            "note": "This is a weak hinge-connectivity proxy. A real hinge model should constrain shared hinge axis/endpoints."
        }

    if whole_metrics["collapse_flag"]:
        overall = "PER_PART_ORACLE_V1_REJECTED_BY_COLLAPSE_GUARD"
    elif any(v == "whole_gt_proxy_no_gt_part_label" for v in target_mode.values()):
        overall = "PER_PART_ORACLE_V1_PROXY_TARGET_VISUAL_CHECK_REQUIRED"
    else:
        overall = "PER_PART_ORACLE_V1_NO_COLLAPSE_FLAG_GT_PART_TARGETS"

    results = {
        "case_id": case_root.name,
        "stage": "Gate D-0 per-part oracle v1",
        "purpose": "test shared-scale per-part rigid alignment before non-GT object repair",
        "important_constraint": "one shared global scale; no independent per-part scale",
        "shared_scale": shared_scale,
        "target_mode": target_mode,
        "transforms": transforms,
        "whole_metrics": whole_metrics,
        "part_metrics": part_metrics,
        "hinge_gap_proxy": hinge_gap,
        "overall_decision": overall,
        "warnings": [
            "This is an oracle diagnostic, not a final method.",
            "If gt_parts are missing, part targets use whole GT object as proxy, so visual inspection is required.",
            "This v1 does not enforce a true connected hinge yet; it reports hinge gap as a proxy."
        ],
    }

    out_json = out_metrics / "gate_d0_per_part_oracle_v1_metrics.json"
    out_json.write_text(json.dumps(results, indent=2))

    scene = trimesh.Scene()
    scene.add_geometry(colorize(gt_object, [180, 180, 180, 90]), node_name="gt_object_gray")
    scene.add_geometry(colorize(transformed_parts["screen"], [0, 0, 255, 180]), node_name="screen_blue")
    scene.add_geometry(colorize(transformed_parts["keyboard_base"], [255, 140, 0, 180]), node_name="keyboard_base_orange")
    if "hinge" in transformed_parts:
        scene.add_geometry(colorize(transformed_parts["hinge"], [255, 0, 255, 200]), node_name="hinge_magenta")
    scene.export(out_vis / "gate_d0_per_part_oracle_v1_scene.glb")

    print("[OK] wrote", out_json)
    print("[OK] wrote", out_vis / "gate_d0_per_part_oracle_v1_scene.glb")
    print("[DECISION]", overall)
    print("[shared_scale]", shared_scale)
    print("[whole collapse]", whole_metrics["collapse_flag"])
    print("[whole pred_to_gt_mean]", whole_metrics["pred_to_gt"]["mean"])
    print("[whole gt_to_pred_mean]", whole_metrics["gt_to_pred"]["mean"])
    print("[whole bbox_volume_ratio]", whole_metrics["bbox"]["bbox_volume_ratio_pred_over_gt"])
    if hinge_gap:
        print("[hinge gap p5]", hinge_gap["screen_to_base_nn_p5"])


if __name__ == "__main__":
    main()
