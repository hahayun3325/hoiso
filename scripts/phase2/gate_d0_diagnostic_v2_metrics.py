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
        geoms = []
        for g in obj.geometry.values():
            if hasattr(g, "vertices") and len(g.vertices) > 0:
                geoms.append(g)
        if not geoms:
            raise ValueError(f"Scene has no valid geometry: {path}")
        mesh = trimesh.util.concatenate(geoms)
    elif isinstance(obj, trimesh.Trimesh):
        mesh = obj
    else:
        raise TypeError(f"Unsupported geometry type for {path}: {type(obj)}")

    if len(mesh.vertices) == 0:
        raise ValueError(f"Mesh has zero vertices: {path}")

    return mesh


def sample_points(mesh: trimesh.Trimesh, n: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)

    if hasattr(mesh, "faces") and len(mesh.faces) > 0:
        n_sample = min(n, max(n, len(mesh.faces)))
        pts, _ = trimesh.sample.sample_surface(mesh, n_sample)
        return np.asarray(pts, dtype=np.float64)

    verts = np.asarray(mesh.vertices, dtype=np.float64)
    if len(verts) <= n:
        return verts
    idx = rng.choice(len(verts), size=n, replace=False)
    return verts[idx]


def nn_dist(src: np.ndarray, tgt: np.ndarray) -> np.ndarray:
    tree = cKDTree(tgt)
    d, _ = tree.query(src, k=1)
    return d


def fscore(d_pred_to_gt: np.ndarray, d_gt_to_pred: np.ndarray, th: float) -> dict:
    precision = float((d_pred_to_gt <= th).mean())
    recall = float((d_gt_to_pred <= th).mean())
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
    pred_bounds = np.asarray(pred.bounds, dtype=np.float64)
    gt_bounds = np.asarray(gt.bounds, dtype=np.float64)

    pred_extent = pred_bounds[1] - pred_bounds[0]
    gt_extent = gt_bounds[1] - gt_bounds[0]

    eps = 1e-12
    axis_ratio = pred_extent / np.maximum(gt_extent, eps)

    pred_vol = float(np.prod(np.maximum(pred_extent, eps)))
    gt_vol = float(np.prod(np.maximum(gt_extent, eps)))
    volume_ratio = pred_vol / max(gt_vol, eps)

    pred_centroid = np.asarray(pred.centroid, dtype=np.float64)
    gt_centroid = np.asarray(gt.centroid, dtype=np.float64)
    centroid_error = float(np.linalg.norm(pred_centroid - gt_centroid))

    return {
        "pred_extent_xyz": pred_extent.tolist(),
        "gt_extent_xyz": gt_extent.tolist(),
        "axis_ratio_pred_over_gt_xyz": axis_ratio.tolist(),
        "axis_ratio_min": float(axis_ratio.min()),
        "axis_ratio_max": float(axis_ratio.max()),
        "bbox_volume_ratio_pred_over_gt": float(volume_ratio),
        "centroid_error": centroid_error,
        "pred_centroid": pred_centroid.tolist(),
        "gt_centroid": gt_centroid.tolist(),
    }


def evaluate_candidate(name: str, pred_path: Path, gt_path: Path, n_points: int) -> dict:
    pred = load_mesh(pred_path)
    gt = load_mesh(gt_path)

    pred_pts = sample_points(pred, n_points, seed=1)
    gt_pts = sample_points(gt, n_points, seed=2)

    d_p2g = nn_dist(pred_pts, gt_pts)
    d_g2p = nn_dist(gt_pts, pred_pts)

    bbox = bbox_stats(pred, gt)

    pred_to_gt_mean = float(d_p2g.mean())
    gt_to_pred_mean = float(d_g2p.mean())
    symmetric_mean = float(0.5 * (pred_to_gt_mean + gt_to_pred_mean))

    asymmetry_ratio = gt_to_pred_mean / max(pred_to_gt_mean, 1e-12)

    # These are diagnostic flags, not final paper thresholds.
    # They are meant to catch the "small/twisted/collapsed but low pred->GT NN" failure.
    collapse_flags = {
        "bbox_volume_too_small": bbox["bbox_volume_ratio_pred_over_gt"] < 0.35,
        "bbox_axis_too_small": bbox["axis_ratio_min"] < 0.40,
        "bbox_axis_too_large": bbox["axis_ratio_max"] > 2.50,
        "gt_to_pred_too_large": gt_to_pred_mean > 0.05,
        "asymmetric_distance_too_large": asymmetry_ratio > 3.0,
    }

    collapse_flag = bool(any(collapse_flags.values()))

    return {
        "name": name,
        "pred_path": str(pred_path),
        "gt_path": str(gt_path),
        "num_pred_vertices": int(len(pred.vertices)),
        "num_gt_vertices": int(len(gt.vertices)),
        "num_pred_sample_points": int(len(pred_pts)),
        "num_gt_sample_points": int(len(gt_pts)),
        "pred_to_gt": {
            "mean": pred_to_gt_mean,
            "median": float(np.median(d_p2g)),
            "p95": float(np.percentile(d_p2g, 95)),
            "max": float(d_p2g.max()),
        },
        "gt_to_pred": {
            "mean": gt_to_pred_mean,
            "median": float(np.median(d_g2p)),
            "p95": float(np.percentile(d_g2p, 95)),
            "max": float(d_g2p.max()),
        },
        "symmetric_mean": symmetric_mean,
        "asymmetry_ratio_gt_to_pred_over_pred_to_gt": float(asymmetry_ratio),
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", required=True)
    parser.add_argument("--n-points", type=int, default=30000)
    args = parser.parse_args()

    case_root = Path(args.case_root)
    repair_root = case_root / "gate_d0_object_repair"
    out_dir = repair_root / "metrics_v2"
    out_dir.mkdir(parents=True, exist_ok=True)

    gt_object = case_root / "gt_reference/selected/gt_object_mesh.ply"

    candidates = {
        "current_phase2_part_scene": case_root / "part_meshes_partfield_v2_vmap/part_scene.glb",
        "oracle_similarity_repaired_object": repair_root / "outputs/object_repaired_oracle_similarity_to_gt.ply",
    }

    results = {
        "case_id": case_root.name,
        "stage": "Gate D-0 diagnostic v2",
        "purpose": "catch collapsed/twisted object repair that one-way NN can miss",
        "gt_object": str(gt_object),
        "candidates": {},
    }

    for name, path in candidates.items():
        if not path.exists():
            results["candidates"][name] = {
                "exists": False,
                "path": str(path),
                "error": "missing file",
            }
            continue

        try:
            results["candidates"][name] = {
                "exists": True,
                **evaluate_candidate(name, path, gt_object, args.n_points),
            }
        except Exception as e:
            results["candidates"][name] = {
                "exists": True,
                "path": str(path),
                "error": repr(e),
            }

    # Overall decision
    oracle = results["candidates"].get("oracle_similarity_repaired_object", {})
    if not oracle.get("exists", False):
        overall = "MISSING_ORACLE_REPAIR"
    elif oracle.get("collapse_flag", False):
        overall = "OLD_ORACLE_REPAIR_REJECTED_BY_V2_METRICS"
    elif "error" in oracle:
        overall = "V2_METRIC_FAILED_ON_ORACLE_REPAIR"
    else:
        overall = "OLD_ORACLE_REPAIR_NOT_COLLAPSED_BY_CURRENT_FLAGS_VISUAL_CHECK_STILL_REQUIRED"

    results["overall_decision"] = overall

    out_json = out_dir / "gate_d0_diagnostic_v2_metrics.json"
    out_json.write_text(json.dumps(results, indent=2))

    print("[OK] wrote", out_json)
    print("[DECISION]", overall)

    for name, r in results["candidates"].items():
        print("\n==", name, "==")
        if "error" in r:
            print("error:", r["error"])
            continue
        print("pred_to_gt_mean:", r["pred_to_gt"]["mean"])
        print("gt_to_pred_mean:", r["gt_to_pred"]["mean"])
        print("symmetric_mean:", r["symmetric_mean"])
        print("bbox_volume_ratio:", r["bbox"]["bbox_volume_ratio_pred_over_gt"])
        print("axis_ratio_min/max:", r["bbox"]["axis_ratio_min"], r["bbox"]["axis_ratio_max"])
        print("collapse_flag:", r["collapse_flag"])
        print("diagnostic_decision:", r["diagnostic_decision"])


if __name__ == "__main__":
    main()
