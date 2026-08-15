#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
from typing import Any

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")

import cv2
import numpy as np
import torch
from scipy.spatial import cKDTree


METRIC_NAMES = [
    "positive_metric_depth_fraction",
    "normalized_metric_depth_residual",
    "full_image_keypoint_nrmse",
    "full_image_keypoint_np95",
    "silhouette_iou",
    "neighbor_crop_consensus",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise TypeError(f"Expected one JSON object: {path}")
    return value


def to_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    return np.asarray(value)


def load_packet_cpu(path: Path) -> dict[str, Any]:
    original = torch.storage._load_from_bytes
    torch.storage._load_from_bytes = lambda payload: torch.load(
        io.BytesIO(payload), map_location="cpu", weights_only=False
    )
    try:
        value = np.load(path, allow_pickle=True)
        if isinstance(value, np.ndarray) and value.shape == ():
            value = value.item()
    finally:
        torch.storage._load_from_bytes = original
    if not isinstance(value, dict):
        raise TypeError(f"Candidate packet must contain one dictionary: {path}")
    return value


def resolve_field(payload: dict[str, Any], field_path: str) -> Any:
    value: Any = payload
    for token in field_path.split("/"):
        if not token or token == "root":
            continue
        if not isinstance(value, dict) or token not in value:
            raise KeyError(f"Packet field does not exist: {field_path}")
        value = value[token]
    return value


def as_points(value: Any, name: str, minimum: int) -> np.ndarray:
    array = np.asarray(to_numpy(value), dtype=np.float64)
    while array.ndim > 2 and array.shape[0] == 1:
        array = array[0]
    if array.ndim != 2 or array.shape[1] != 3 or array.shape[0] < minimum:
        raise ValueError(f"{name} must be Nx3 with N >= {minimum}, got {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains non-finite values")
    return array


def flag_value(argv: list[str], flag: str) -> str:
    index = argv.index(flag)
    return argv[index + 1]


def factor_similarity(matrix: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
        raise ValueError("H2M must be one finite 4x4 matrix")
    if not np.allclose(matrix[3], [0.0, 0.0, 0.0, 1.0], atol=1e-6):
        raise ValueError("H2M is not homogeneous")
    u, singular_values, vt = np.linalg.svd(matrix[:3, :3])
    rotation = u @ vt
    if np.linalg.det(rotation) < 0:
        u[:, -1] *= -1.0
        rotation = u @ vt
    scale = float(np.mean(singular_values))
    spread = float((singular_values.max() - singular_values.min()) / scale)
    reconstruction = float(
        np.linalg.norm(matrix[:3, :3] - scale * rotation)
        / np.linalg.norm(matrix[:3, :3])
    )
    if spread > 1e-4 or reconstruction > 1e-4 or np.linalg.det(rotation) <= 0:
        raise ValueError("H2M is not the frozen proper uniform similarity")
    return scale, rotation, matrix[:3, 3].copy()


def apply_similarity(
    points: np.ndarray, scale: float, rotation: np.ndarray, translation: np.ndarray
) -> np.ndarray:
    return scale * (points @ rotation.T) + translation.reshape(1, 3)


def load_metric_points(
    points_path: Path, mask_path: Path, maximum: int, seed: int
) -> np.ndarray:
    points = cv2.imread(str(points_path), cv2.IMREAD_UNCHANGED)
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if points is None or mask is None:
        raise ValueError("Unable to decode the frozen MoGe points or hand mask")
    points = np.asarray(points, dtype=np.float64)
    mask = np.asarray(mask) > 0
    if points.ndim != 3 or points.shape[:2] != mask.shape or points.shape[2] < 3:
        raise ValueError(f"MoGe points/mask mismatch: {points.shape} versus {mask.shape}")
    selected = points[..., :3][mask]
    selected = selected[np.isfinite(selected).all(axis=1)]
    if selected.shape[0] < 21:
        raise ValueError("Fewer than 21 finite masked metric points remain")
    if selected.shape[0] > maximum:
        rng = np.random.default_rng(seed)
        indices = np.sort(rng.choice(selected.shape[0], size=maximum, replace=False))
        selected = selected[indices]
    return selected


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    ordered_values = values[order]
    ordered_weights = weights[order]
    cumulative = np.cumsum(ordered_weights) / np.sum(ordered_weights)
    index = int(np.searchsorted(cumulative, q, side="left"))
    return float(ordered_values[min(index, ordered_values.size - 1)])


def robust_threshold(
    values: np.ndarray, positive_control_value: float, direction: str
) -> dict[str, float]:
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    robust_sigma = 1.4826 * mad
    floating_floor = float(
        64.0
        * np.finfo(np.float64).eps
        * max(1.0, abs(positive_control_value), abs(median))
    )
    envelope = 3.0 * robust_sigma + floating_floor
    if direction == "lower_is_better":
        threshold = max(positive_control_value, median + envelope)
    elif direction == "higher_is_better":
        threshold = min(positive_control_value, median - envelope)
    else:
        raise ValueError(f"Unknown metric direction: {direction}")
    return {
        "threshold": float(threshold),
        "positive_control_value": float(positive_control_value),
        "family_median": median,
        "family_MAD": mad,
        "robust_sigma": robust_sigma,
        "floating_floor": floating_floor,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--metrics-out", type=Path, required=True)
    parser.add_argument("--thresholds-out", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    args = parser.parse_args()

    input_paths = (args.policy, args.manifest, args.registry, args.target)
    if any(not path.is_file() for path in input_paths):
        raise FileNotFoundError("One or more frozen analyzer inputs are missing")
    output_paths = (args.metrics_out, args.thresholds_out, args.report_out)
    if any(path.exists() for path in output_paths):
        raise FileExistsError("One or more calibration outputs already exist")

    policy = load_json(args.policy)
    manifest = load_json(args.manifest)
    registry = load_json(args.registry)
    if policy.get("decision") != "pass_v99_11_7_9_8_six_metric_v6_calibration_policy_preregistered":
        raise ValueError("Calibration policy is not passed")
    if [item.get("name") for item in policy.get("metrics_in_order", [])] != METRIC_NAMES:
        raise ValueError("The six metric names or order changed")
    if policy.get("scope") != "v6_only_frozen_15_member_family_no_v3_visibility":
        raise ValueError("Calibration scope is not the frozen v6-only family")

    candidate_order = policy.get("candidate_order", [])
    records = registry.get("commands", [])
    packet_by_uid = {item["candidate_uid"]: item for item in manifest.get("packets", [])}
    if len(candidate_order) != 15 or [item.get("candidate_uid") for item in records] != candidate_order:
        raise ValueError("Registry does not preserve the exact 15-candidate order")
    if set(packet_by_uid) != set(candidate_order):
        raise ValueError("Packet manifest does not bind the exact candidate family")

    with np.load(args.target, allow_pickle=False) as target:
        target_xy = np.asarray(target["keypoints_xy_full_image_px_21x2"], dtype=np.float64)
        confidence = np.asarray(target["confidence_21"], dtype=np.float64)
        visibility = np.asarray(target["visibility_21"], dtype=bool)
    if target_xy.shape != (21, 2) or confidence.shape != (21,) or visibility.shape != (21,):
        raise ValueError("Independent target shape contract failed")
    weights = np.where(visibility, confidence, 0.0)
    if not np.isfinite(target_xy).all() or not np.isfinite(weights).all() or np.any(weights < 0) or float(weights.sum()) <= 0:
        raise ValueError("Independent target values or weights are invalid")
    palm_width_px = float(np.linalg.norm(target_xy[5] - target_xy[17]))
    if not math.isfinite(palm_width_px) or palm_width_px <= 0:
        raise ValueError("Frozen v6 palm width is not positive and finite")

    common_signature = None
    metric_points = None
    hand_depth_scale = None
    candidate_rows: list[dict[str, Any]] = []
    normalized_joints: list[np.ndarray] = []
    normalized_vertices: list[np.ndarray] = []

    for record in records:
        uid = record["candidate_uid"]
        argv = list(record["argv"])
        candidate_path = Path(flag_value(argv, "--candidate"))
        target_path = Path(flag_value(argv, "--target"))
        h2m_path = Path(flag_value(argv, "--H2M"))
        points_path = Path(flag_value(argv, "--moge-points"))
        mask_path = Path(flag_value(argv, "--hand-mask"))
        config_path = Path(flag_value(argv, "--config"))
        result_path = Path(record["result_out"])
        raw_report_path = Path(record["report_out"])
        required = (candidate_path, target_path, h2m_path, points_path, mask_path, config_path, result_path, raw_report_path)
        if any(not path.is_file() for path in required):
            raise FileNotFoundError(f"{uid}: one or more frozen inputs are missing")
        packet_record = packet_by_uid[uid]
        if candidate_path != Path(packet_record["path"]) or sha256(candidate_path) != packet_record["sha256"]:
            raise ValueError(f"{uid}: candidate packet provenance mismatch")
        if target_path.resolve() != args.target.resolve():
            raise ValueError(f"{uid}: target path differs from the frozen common target")

        config = load_json(config_path)
        raw_report = load_json(raw_report_path)
        if raw_report.get("decision") != "pass_v99_11_7_5_bounded_metric_reanchor_raw_result":
            raise ValueError(f"{uid}: raw reanchor report is not passed")
        signature = (
            str(h2m_path.resolve()), sha256(h2m_path),
            str(points_path.resolve()), sha256(points_path),
            str(mask_path.resolve()), sha256(mask_path),
            int(config["metric_max_points"]), int(config["metric_sample_seed"]),
            float(config["metric_residual_clip"]),
        )
        if common_signature is None:
            common_signature = signature
            metric_points = load_metric_points(
                points_path,
                mask_path,
                int(config["metric_max_points"]),
                int(config["metric_sample_seed"]),
            )
            hand_depth_scale = float(
                np.quantile(metric_points[:, 2], 0.95)
                - np.quantile(metric_points[:, 2], 0.05)
            )
            if not math.isfinite(hand_depth_scale) or hand_depth_scale <= 0:
                raise ValueError("Frozen v6 hand depth scale is not positive and finite")
        elif signature != common_signature:
            raise ValueError(f"{uid}: common metric resource or sampling contract changed")

        with np.load(result_path, allow_pickle=False) as result:
            scale = float(np.asarray(result["relative_metric_scale"]).reshape(()))
            translation = np.asarray(result["translation_xyz"], dtype=np.float64)
            fixed_joints = np.asarray(result["fixed_oriented_joints_21x3"], dtype=np.float64)
            projected = np.asarray(result["projected_keypoints_21x2"], dtype=np.float64)
            positive_fraction = float(np.asarray(result["positive_depth_fraction"]).reshape(()))
        if translation.shape != (3,) or fixed_joints.shape != (21, 3) or projected.shape != (21, 2):
            raise ValueError(f"{uid}: raw result shape contract failed")
        if not all(np.isfinite(value).all() for value in (translation, fixed_joints, projected)):
            raise ValueError(f"{uid}: raw result contains non-finite values")

        packet = load_packet_cpu(candidate_path)
        fields = config["packet_fields"]
        vertices = as_points(resolve_field(packet, fields["vertices"]), "vertices", 100)
        joints = as_points(resolve_field(packet, fields["joints_3d"]), "joints_3d", 21)
        if joints.shape != (21, 3):
            raise ValueError(f"{uid}: packet joints are not exactly 21x3")
        h2m = np.asarray(np.load(h2m_path), dtype=np.float64)
        h2m_scale, h2m_rotation, h2m_translation = factor_similarity(h2m)
        vertices_moge = apply_similarity(vertices, h2m_scale, h2m_rotation, h2m_translation)
        joints_moge = apply_similarity(joints, h2m_scale, h2m_rotation, h2m_translation)
        scaled_vertices_moge = joints_moge[0] + scale * (vertices_moge - joints_moge[0])
        distances, _ = cKDTree(metric_points).query(scaled_vertices_moge, k=1, workers=1)
        clipped = np.minimum(np.asarray(distances, dtype=np.float64), float(config["metric_residual_clip"]))
        depth_residual = float(np.sqrt(np.mean(clipped ** 2)) / hand_depth_scale)

        keypoint_errors = np.linalg.norm(projected - target_xy, axis=1)
        keypoint_nrmse = float(np.sqrt(np.sum(weights * keypoint_errors ** 2) / np.sum(weights)) / palm_width_px)
        keypoint_np95 = float(weighted_quantile(keypoint_errors, weights, 0.95) / palm_width_px)

        palm_metric_width = float(np.linalg.norm(fixed_joints[5] - fixed_joints[17]))
        if not math.isfinite(palm_metric_width) or palm_metric_width <= 0:
            raise ValueError(f"{uid}: metric palm width is not positive and finite")
        normalized_joints.append(fixed_joints / palm_metric_width)
        normalized_vertices.append(scale * (vertices - joints[0]) / palm_metric_width)
        candidate_rows.append({
            "candidate_uid": uid,
            "ordinal": int(record["ordinal"]),
            "metrics": {
                "positive_metric_depth_fraction": positive_fraction,
                "normalized_metric_depth_residual": depth_residual,
                "full_image_keypoint_nrmse": keypoint_nrmse,
                "full_image_keypoint_np95": keypoint_np95,
                "silhouette_iou": None,
                "neighbor_crop_consensus": None,
            },
            "raw_result": {"path": str(result_path), "sha256": sha256(result_path)},
            "raw_report": {"path": str(raw_report_path), "sha256": sha256(raw_report_path)},
            "candidate_packet": {"path": str(candidate_path), "sha256": sha256(candidate_path)},
        })

    vertex_shapes = {array.shape for array in normalized_vertices}
    if len(vertex_shapes) != 1:
        raise ValueError("Candidate meshes do not share one vertex topology")
    count = len(candidate_rows)
    pairwise = np.zeros((count, count), dtype=np.float64)
    for left in range(count):
        for right in range(left + 1, count):
            joint_distance = float(np.sqrt(np.mean((normalized_joints[left] - normalized_joints[right]) ** 2)))
            vertex_distance = float(np.median(np.linalg.norm(normalized_vertices[left] - normalized_vertices[right], axis=1)))
            value = 0.5 * (joint_distance + vertex_distance)
            pairwise[left, right] = pairwise[right, left] = value
    medoid_scores = np.median(pairwise, axis=1)
    minimum_score = float(np.min(medoid_scores))
    tie_floor = 64.0 * np.finfo(np.float64).eps * max(1.0, abs(minimum_score))
    medoid_indices = np.flatnonzero(np.abs(medoid_scores - minimum_score) <= tie_floor)
    for index, row in enumerate(candidate_rows):
        row["metrics"]["neighbor_crop_consensus"] = float(np.min(pairwise[index, medoid_indices]))

    metric_directions = {item["name"]: item["direction"] for item in policy["metrics_in_order"]}
    baseline_uid = policy["positive_control"]
    baseline_index = candidate_order.index(baseline_uid)
    thresholds: dict[str, Any] = {}
    for name in METRIC_NAMES:
        if name == "silhouette_iou":
            thresholds[name] = {
                "active": False,
                "threshold": None,
                "reason": "no_independent_authoritative_full_image_hand_mask_was_prebound",
            }
            continue
        values = np.asarray([row["metrics"][name] for row in candidate_rows], dtype=np.float64)
        if values.shape != (15,) or not np.isfinite(values).all():
            raise ValueError(f"{name}: metric family is incomplete or non-finite")
        threshold = robust_threshold(values, float(values[baseline_index]), metric_directions[name])
        threshold.update({"active": True, "direction": metric_directions[name]})
        thresholds[name] = threshold

    metrics_document = {
        "schema": "six_metric_v6_candidate_table_v99_11_7_9_9",
        "decision": "pass_v99_11_7_9_9_six_metric_values_materialized",
        "candidate_order": candidate_order,
        "positive_control": baseline_uid,
        "normalizers": {
            "frozen_v6_palm_width_px": palm_width_px,
            "frozen_v6_hand_depth_scale": hand_depth_scale,
            "neighbor_medoid_candidates": [candidate_order[index] for index in medoid_indices.tolist()],
        },
        "candidates": candidate_rows,
        "silhouette_status": "not_applicable_no_authoritative_full_image_mask_bound",
        "authorizes_candidate_selection": False,
        "authorizes_v3": False,
        "authorizes_optimizer": False,
    }
    threshold_document = {
        "schema": "six_metric_v6_threshold_bundle_v99_11_7_9_9",
        "decision": "pass_v99_11_7_9_9_six_metric_thresholds_fitted_v6_only",
        "calibration_population": candidate_order,
        "positive_control": baseline_uid,
        "threshold_rule": policy["threshold_rule"],
        "thresholds": thresholds,
        "numeric_active_thresholds_complete": all(
            thresholds[name]["active"] and math.isfinite(float(thresholds[name]["threshold"]))
            for name in METRIC_NAMES if name != "silhouette_iou"
        ),
        "silhouette_is_conditionally_inactive": thresholds["silhouette_iou"]["active"] is False,
        "authorizes_candidate_selection": False,
        "authorizes_v3": False,
        "authorizes_optimizer": False,
    }
    for path in output_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_out.write_text(json.dumps(metrics_document, indent=2) + "\n")
    args.thresholds_out.write_text(json.dumps(threshold_document, indent=2) + "\n")
    report = {
        "schema": "six_metric_v6_calibration_analyzer_report_v99_11_7_9_9",
        "decision": "pass_v99_11_7_9_9_cpu_six_metric_v6_calibration",
        "inputs": {str(path): sha256(path) for path in input_paths},
        "metrics": {"path": str(args.metrics_out), "sha256": sha256(args.metrics_out)},
        "thresholds": {"path": str(args.thresholds_out), "sha256": sha256(args.thresholds_out)},
        "candidate_count": count,
        "active_threshold_count": 5,
        "silhouette_status": metrics_document["silhouette_status"],
        "selection_performed": False,
        "authorizes_candidate_selection": False,
        "authorizes_v3": False,
        "authorizes_optimizer": False,
    }
    args.report_out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"decision={report['decision']} candidates={count} active_thresholds=5 selection=False")


if __name__ == "__main__":
    main()
