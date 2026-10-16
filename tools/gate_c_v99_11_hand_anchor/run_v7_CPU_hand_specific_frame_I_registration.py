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

os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")

import cv2
import numpy as np
from scipy import optimize
from scipy.spatial import cKDTree


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_packet_cpu(path: Path) -> dict[str, Any]:
    try:
        import torch

        original = torch.load

        def load_from_bytes(blob):
            kwargs = {"map_location": torch.device("cpu")}
            try:
                return original(io.BytesIO(blob), weights_only=False, **kwargs)
            except TypeError:
                return original(io.BytesIO(blob), **kwargs)

        torch.storage._load_from_bytes = load_from_bytes
    except ImportError:
        pass
    payload = np.load(path, allow_pickle=True)
    if isinstance(payload, np.ndarray) and payload.shape == ():
        payload = payload.item()
    if not isinstance(payload, dict):
        raise ValueError("Candidate packet must contain one dictionary")
    return payload


def resolve_field(payload: dict[str, Any], path: str) -> Any:
    value: Any = payload
    for token in path.split("/"):
        if not token or token == "root":
            continue
        if not isinstance(value, dict) or token not in value:
            raise KeyError(f"Packet field does not exist: {path}")
        value = value[token]
    return value


def as_points(value: Any, name: str, minimum: int) -> np.ndarray:
    if hasattr(value, "detach") and hasattr(value, "cpu"):
        value = value.detach().cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    array = np.asarray(value, dtype=np.float64)
    while array.ndim > 2 and array.shape[0] == 1:
        array = array[0]
    if array.ndim != 2 or array.shape[1] != 3 or array.shape[0] < minimum:
        raise ValueError(f"{name} must be Nx3 with N >= {minimum}, got {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains non-finite values")
    return array


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    required = {
        "schema",
        "candidate_execution_authorized",
        "expected_candidate_sha256",
        "expected_target_sha256",
        "expected_points_sha256",
        "expected_hand_mask_sha256",
        "packet_fields",
        "joint_map_21",
        "minimum_visible_joints",
        "minimum_anchor_joints",
        "anchor_window_radius_px",
        "scale_multiplier_bounds",
        "rotation_component_bounds_radians",
        "translation_support_extent_multiplier",
        "anchor_3d_weight",
        "reprojection_weight",
        "surface_support_weight",
        "log_scale_prior_weight",
        "surface_max_points",
        "surface_sample_seed",
        "surface_residual_clip_normalized",
        "maximum_nfev",
        "minimum_positive_camera_depth_fraction",
        "maximum_keypoint_nrmse",
        "maximum_anchor_nrmse",
        "maximum_surface_nrmse",
        "minimum_projected_vertex_mask_fraction",
        "scale_bound_margin_fraction",
    }
    missing = sorted(required - set(data))
    nulls = sorted(key for key in required if key in data and data[key] is None)
    if missing or nulls:
        raise ValueError(f"Hand-specific policy incomplete: missing={missing} null={nulls}")
    if data["schema"] != "tracehoi.HandSpecificFrameIPolicy.v1":
        raise ValueError("Unexpected hand-specific policy schema")
    if type(data["candidate_execution_authorized"]) is not bool:
        raise ValueError("candidate_execution_authorized must be Boolean")
    fields = data["packet_fields"]
    if set(fields) != {"vertices", "joints_3d", "focal_length"}:
        raise ValueError("packet_fields must bind vertices, joints_3d, and focal_length")
    joint_map = np.asarray(data["joint_map_21"], dtype=np.int64)
    if joint_map.shape != (21,) or sorted(joint_map.tolist()) != list(range(21)):
        raise ValueError("joint_map_21 must be a permutation of 0..20")
    scale_bounds = np.asarray(data["scale_multiplier_bounds"], dtype=np.float64)
    rotation_bounds = np.asarray(data["rotation_component_bounds_radians"], dtype=np.float64)
    if scale_bounds.shape != (2,) or not 0 < scale_bounds[0] < 1 < scale_bounds[1]:
        raise ValueError("scale_multiplier_bounds must straddle one and remain positive")
    if rotation_bounds.shape != (2,) or not rotation_bounds[0] < 0 < rotation_bounds[1]:
        raise ValueError("rotation_component_bounds_radians must straddle zero")
    positive = (
        "minimum_visible_joints",
        "minimum_anchor_joints",
        "anchor_window_radius_px",
        "translation_support_extent_multiplier",
        "anchor_3d_weight",
        "reprojection_weight",
        "surface_support_weight",
        "log_scale_prior_weight",
        "surface_max_points",
        "surface_residual_clip_normalized",
        "maximum_nfev",
        "minimum_positive_camera_depth_fraction",
        "maximum_keypoint_nrmse",
        "maximum_anchor_nrmse",
        "maximum_surface_nrmse",
        "minimum_projected_vertex_mask_fraction",
        "scale_bound_margin_fraction",
    )
    if any(not math.isfinite(float(data[key])) or float(data[key]) <= 0 for key in positive):
        raise ValueError("Operational thresholds must be finite and positive")
    return data


def decode_moge_points(raw_bgr: np.ndarray) -> np.ndarray:
    raw = np.asarray(raw_bgr, dtype=np.float64)
    if raw.ndim != 3 or raw.shape[2] < 3:
        raise ValueError(f"MoGe point map must be HxWx3, got {raw.shape}")
    camera_xyz = raw[..., :3][..., ::-1]
    native = camera_xyz * np.asarray([1.0, -1.0, -1.0], dtype=np.float64)
    return native


def load_moge_support(points_path: Path, mask_path: Path) -> tuple[np.ndarray, np.ndarray]:
    points = cv2.imread(str(points_path), cv2.IMREAD_UNCHANGED)
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if points is None or mask is None:
        raise ValueError("Unable to read MoGe points or selected-hand mask")
    native = decode_moge_points(points)
    selected = np.asarray(mask) > 0
    if native.shape[:2] != selected.shape:
        raise ValueError(f"MoGe/mask shape mismatch: {native.shape} versus {selected.shape}")
    return native, selected


def collect_joint_anchors(
    point_map: np.ndarray,
    hand_mask: np.ndarray,
    target_xy: np.ndarray,
    visibility: np.ndarray,
    confidence: np.ndarray,
    radius: int,
    minimum: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    height, width = hand_mask.shape
    anchors, indices, weights, pixels = [], [], [], []
    for index, (xy, visible, score) in enumerate(zip(target_xy, visibility, confidence)):
        if not visible or not np.isfinite(xy).all() or not math.isfinite(float(score)):
            continue
        x, y = int(round(float(xy[0]))), int(round(float(xy[1])))
        x0, x1 = max(0, x - radius), min(width, x + radius + 1)
        y0, y1 = max(0, y - radius), min(height, y + radius + 1)
        if x0 >= x1 or y0 >= y1:
            continue
        local_points = point_map[y0:y1, x0:x1]
        local_mask = hand_mask[y0:y1, x0:x1]
        valid = local_mask & np.isfinite(local_points).all(axis=2)
        values = local_points[valid]
        if values.shape[0] == 0:
            continue
        anchors.append(np.median(values, axis=0))
        indices.append(index)
        weights.append(float(np.clip(score, 1e-6, 1.0)))
        pixels.append(np.asarray(xy, dtype=np.float64))
    if len(anchors) < minimum:
        raise ValueError(f"Only {len(anchors)} metric joint anchors are available; need {minimum}")
    return (
        np.asarray(anchors, dtype=np.float64),
        np.asarray(indices, dtype=np.int64),
        np.asarray(weights, dtype=np.float64),
        np.asarray(pixels, dtype=np.float64),
    )


def weighted_umeyama(source: np.ndarray, target: np.ndarray, weights: np.ndarray):
    source = np.asarray(source, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64).reshape(-1)
    if source.shape != target.shape or source.ndim != 2 or source.shape[1] != 3:
        raise ValueError("Umeyama inputs must be matching Nx3 arrays")
    if weights.shape != (source.shape[0],) or not np.isfinite(weights).all() or np.any(weights <= 0):
        raise ValueError("Umeyama weights must be one positive finite value per point")
    weights = weights / weights.sum()
    source_mean = np.sum(weights[:, None] * source, axis=0)
    target_mean = np.sum(weights[:, None] * target, axis=0)
    source_centered = source - source_mean
    target_centered = target - target_mean
    covariance = (weights[:, None] * target_centered).T @ source_centered
    u, singular, vt = np.linalg.svd(covariance)
    sign = np.ones(3, dtype=np.float64)
    if np.linalg.det(u @ vt) < 0:
        sign[-1] = -1.0
    rotation = u @ np.diag(sign) @ vt
    variance = float(np.sum(weights * np.sum(source_centered**2, axis=1)))
    if not math.isfinite(variance) or variance <= 1e-12:
        raise ValueError("Source anchors have zero spread")
    scale = float(np.sum(singular * sign) / variance)
    translation = target_mean - scale * (rotation @ source_mean)
    if not math.isfinite(scale) or scale <= 0 or np.linalg.det(rotation) <= 0:
        raise ValueError("Umeyama did not produce a positive proper similarity")
    return scale, rotation, translation


def rotation_vector(matrix: np.ndarray) -> np.ndarray:
    vector, _ = cv2.Rodrigues(np.asarray(matrix, dtype=np.float64))
    return np.asarray(vector, dtype=np.float64).reshape(3)


def rotation_matrix(vector: np.ndarray) -> np.ndarray:
    matrix, _ = cv2.Rodrigues(np.asarray(vector, dtype=np.float64).reshape(3, 1))
    matrix = np.asarray(matrix, dtype=np.float64)
    if not np.isclose(np.linalg.det(matrix), 1.0, atol=1e-8):
        raise ValueError("Rotation is not proper")
    return matrix


def apply_similarity(points: np.ndarray, parameter: np.ndarray) -> np.ndarray:
    parameter = np.asarray(parameter, dtype=np.float64).reshape(7)
    scale = float(np.exp(parameter[0]))
    rotation = rotation_matrix(parameter[1:4])
    return scale * (np.asarray(points, dtype=np.float64) @ rotation.T) + parameter[4:7]


def camera_intrinsic(focal: Any, image_size_wh: np.ndarray) -> np.ndarray:
    if hasattr(focal, "detach") and hasattr(focal, "cpu"):
        focal = focal.detach().cpu()
    if hasattr(focal, "numpy"):
        focal = focal.numpy()
    values = np.asarray(focal, dtype=np.float64).reshape(-1)
    if values.size == 1:
        fx = fy = float(values[0])
    elif values.size >= 2:
        fx, fy = map(float, values[:2])
    else:
        raise ValueError("focal_length is empty")
    width, height = map(float, image_size_wh)
    if min(fx, fy, width, height) <= 0:
        raise ValueError("Invalid focal length or image size")
    return np.asarray([[fx, 0, width / 2], [0, fy, height / 2], [0, 0, 1]], dtype=np.float64)


def recover_moge_intrinsic(point_map: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    native = np.asarray(point_map, dtype=np.float64)
    if native.ndim != 3 or native.shape[2] != 3:
        raise ValueError(f"Native MoGe point map must be HxWx3, got {native.shape}")
    camera = native * np.asarray([1.0, -1.0, -1.0], dtype=np.float64)
    height, width = camera.shape[:2]
    yy, xx = np.indices((height, width), dtype=np.float64)
    valid = np.isfinite(camera).all(axis=2) & (camera[..., 2] > 1e-8)
    if int(valid.sum()) < 16:
        raise ValueError("Too few finite positive-depth MoGe samples to recover the intrinsic")
    x_over_z = camera[..., 0][valid] / camera[..., 2][valid]
    y_over_z = camera[..., 1][valid] / camera[..., 2][valid]
    design_x = np.column_stack((x_over_z, np.ones(x_over_z.shape[0], dtype=np.float64)))
    design_y = np.column_stack((y_over_z, np.ones(y_over_z.shape[0], dtype=np.float64)))
    fit_x, _, rank_x, _ = np.linalg.lstsq(design_x, xx[valid], rcond=None)
    fit_y, _, rank_y, _ = np.linalg.lstsq(design_y, yy[valid], rcond=None)
    if rank_x != 2 or rank_y != 2:
        raise ValueError("MoGe point map does not span a recoverable pinhole intrinsic")
    fx, cx = map(float, fit_x)
    fy, cy = map(float, fit_y)
    intrinsic = np.asarray([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64)
    if not np.isfinite(intrinsic).all() or fx <= 0 or fy <= 0:
        raise ValueError("Recovered MoGe intrinsic is not finite and positive")
    predicted_x = design_x @ fit_x
    predicted_y = design_y @ fit_y
    rmse = float(np.sqrt(np.mean((predicted_x - xx[valid]) ** 2 + (predicted_y - yy[valid]) ** 2)))
    if not math.isfinite(rmse) or rmse > 1e-3:
        raise ValueError(f"Recovered MoGe intrinsic exceeds 1e-3 pixel RMSE: {rmse}")
    return intrinsic, {
        "finite_positive_depth_sample_count": int(valid.sum()),
        "pointmap_self_reprojection_rmse_px": rmse,
        "maximum_allowed_rmse_px": 1e-3,
    }


def project_native(points: np.ndarray, intrinsic: np.ndarray) -> np.ndarray:
    camera = np.asarray(points, dtype=np.float64) * np.asarray([1.0, -1.0, -1.0])
    if np.any(camera[:, 2] <= 0):
        return np.full((camera.shape[0], 2), 1e9, dtype=np.float64)
    homogeneous = camera @ np.asarray(intrinsic, dtype=np.float64).T
    return homogeneous[:, :2] / homogeneous[:, 2:3]


def deterministic_sample(points: np.ndarray, maximum: int, seed: int) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    if points.shape[0] <= maximum:
        return points
    rng = np.random.default_rng(seed)
    return points[np.sort(rng.choice(points.shape[0], size=maximum, replace=False))]


def fit_hand_similarity(
    *, vertices: np.ndarray, joints: np.ndarray, anchors: np.ndarray,
    anchor_indices: np.ndarray, anchor_weights: np.ndarray, target_pixels: np.ndarray,
    metric_support: np.ndarray, intrinsic: np.ndarray, config: dict[str, Any]
):
    source_anchors = joints[anchor_indices]
    initial_scale, initial_rotation, initial_translation = weighted_umeyama(
        source_anchors, anchors, anchor_weights
    )
    initial = np.concatenate(
        ([math.log(initial_scale)], rotation_vector(initial_rotation), initial_translation)
    )
    scale_multipliers = np.asarray(config["scale_multiplier_bounds"], dtype=np.float64)
    rotation_bounds = np.asarray(config["rotation_component_bounds_radians"], dtype=np.float64)
    support_diagonal = float(np.linalg.norm(np.ptp(metric_support, axis=0)))
    if not math.isfinite(support_diagonal) or support_diagonal <= 1e-8:
        raise ValueError("Selected MoGe hand support has zero metric extent")
    translation_extent = float(config["translation_support_extent_multiplier"]) * support_diagonal
    lower = np.concatenate(
        ([math.log(initial_scale * scale_multipliers[0])], np.full(3, rotation_bounds[0]), initial_translation - translation_extent)
    )
    upper = np.concatenate(
        ([math.log(initial_scale * scale_multipliers[1])], np.full(3, rotation_bounds[1]), initial_translation + translation_extent)
    )
    initial = np.clip(initial, lower, upper)
    visible_span = float(np.linalg.norm(np.ptp(target_pixels, axis=0)))
    if not math.isfinite(visible_span) or visible_span <= 1e-8:
        raise ValueError("Visible keypoints have zero image-space extent")
    seed = int(config["surface_sample_seed"])
    maximum = int(config["surface_max_points"])
    sampled_vertices = deterministic_sample(vertices, maximum, seed)
    sampled_support = deterministic_sample(metric_support, maximum, seed + 1)
    anchor_weight = float(config["anchor_3d_weight"])
    reprojection_weight = float(config["reprojection_weight"])
    surface_weight = float(config["surface_support_weight"])
    scale_prior_weight = float(config["log_scale_prior_weight"])
    surface_clip = float(config["surface_residual_clip_normalized"])
    confidence = np.sqrt(anchor_weights)[:, None]

    def residual(parameter: np.ndarray) -> np.ndarray:
        aligned_anchors = apply_similarity(source_anchors, parameter)
        anchor_residual = anchor_weight * confidence * (aligned_anchors - anchors) / support_diagonal
        projected = project_native(aligned_anchors, intrinsic)
        reprojection = reprojection_weight * confidence[:, :1] * (projected - target_pixels) / visible_span
        aligned_vertices = apply_similarity(sampled_vertices, parameter)
        model_to_support = cKDTree(sampled_support).query(aligned_vertices, k=1, workers=1)[0]
        support_to_model = cKDTree(aligned_vertices).query(sampled_support, k=1, workers=1)[0]
        surface = surface_weight * np.minimum(
            np.concatenate((model_to_support, support_to_model)) / support_diagonal,
            surface_clip,
        )
        scale_prior = np.asarray([scale_prior_weight * (parameter[0] - math.log(initial_scale))])
        return np.concatenate((anchor_residual.ravel(), reprojection.ravel(), surface, scale_prior))

    result = optimize.least_squares(
        residual,
        x0=initial,
        bounds=(lower, upper),
        method="trf",
        loss="soft_l1",
        f_scale=1.0,
        max_nfev=int(config["maximum_nfev"]),
    )
    if not result.success or result.x.shape != (7,) or not np.isfinite(result.x).all():
        raise RuntimeError(f"Hand-specific Sim(3) fit failed: {result.status} {result.message}")
    return result.x, result, {
        "initial_scale": initial_scale,
        "support_diagonal": support_diagonal,
        "visible_span_px": visible_span,
        "lower": lower,
        "upper": upper,
    }


def projected_mask_fraction(points: np.ndarray, intrinsic: np.ndarray, mask: np.ndarray) -> float:
    projected = project_native(points, intrinsic)
    finite = np.isfinite(projected).all(axis=1) & (np.abs(projected).max(axis=1) < 1e8)
    rounded = np.rint(projected).astype(np.int64)
    height, width = mask.shape
    inside = finite & (rounded[:, 0] >= 0) & (rounded[:, 0] < width) & (rounded[:, 1] >= 0) & (rounded[:, 1] < height)
    selected = np.zeros(points.shape[0], dtype=bool)
    valid_indices = np.flatnonzero(inside)
    selected[valid_indices] = mask[rounded[valid_indices, 1], rounded[valid_indices, 0]]
    return float(np.mean(selected))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--moge-points", type=Path, required=True)
    parser.add_argument("--hand-mask", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--result-out", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    args = parser.parse_args()
    config = load_config(args.config)
    if config["candidate_execution_authorized"] is not True:
        raise PermissionError("Case-level hand-specific solver execution is not authorized")
    inputs = {
        "candidate": (args.candidate, config["expected_candidate_sha256"]),
        "target": (args.target, config["expected_target_sha256"]),
        "moge_points": (args.moge_points, config["expected_points_sha256"]),
        "hand_mask": (args.hand_mask, config["expected_hand_mask_sha256"]),
    }
    for name, (path, expected) in inputs.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing {name}: {path}")
        if sha256(path) != expected:
            raise ValueError(f"Hash mismatch for {name}")
    if args.result_out.exists() or args.report_out.exists():
        raise FileExistsError("Result or report output already exists")

    packet = load_packet_cpu(args.candidate)
    fields = config["packet_fields"]
    vertices = as_points(resolve_field(packet, fields["vertices"]), "vertices", 100)
    joints = as_points(resolve_field(packet, fields["joints_3d"]), "joints_3d", 21)
    if joints.shape != (21, 3):
        raise ValueError(f"Expected exactly 21x3 joints, got {joints.shape}")
    focal = resolve_field(packet, fields["focal_length"])
    with np.load(args.target, allow_pickle=False) as target:
        target_xy = np.asarray(target["keypoints_xy_full_image_px_21x2"], dtype=np.float64)
        confidence = np.asarray(target["confidence_21"], dtype=np.float64)
        visibility = np.asarray(target["visibility_21"], dtype=bool)
        image_size_wh = np.asarray(target["image_size_wh"], dtype=np.int64)
    if target_xy.shape != (21, 2) or confidence.shape != (21,) or visibility.shape != (21,) or image_size_wh.shape != (2,):
        raise ValueError("Independent target shape contract failed")
    point_map, hand_mask = load_moge_support(args.moge_points, args.hand_mask)
    if tuple(image_size_wh.tolist()) != (point_map.shape[1], point_map.shape[0]):
        raise ValueError("ViTPose target and MoGe point map do not share image dimensions")
    joint_map = np.asarray(config["joint_map_21"], dtype=np.int64)
    ordered_joints = joints[joint_map]
    anchors, anchor_indices, anchor_weights, target_pixels = collect_joint_anchors(
        point_map,
        hand_mask,
        target_xy,
        visibility,
        confidence,
        int(config["anchor_window_radius_px"]),
        int(config["minimum_anchor_joints"]),
    )
    metric_support = point_map[hand_mask & np.isfinite(point_map).all(axis=2)]
    if metric_support.shape[0] < int(config["minimum_visible_joints"]):
        raise ValueError("Too few finite selected-hand MoGe support points")
    source_hamer_intrinsic = camera_intrinsic(focal, image_size_wh)
    intrinsic, intrinsic_recovery = recover_moge_intrinsic(point_map)
    parameter, solver, fit = fit_hand_similarity(
        vertices=vertices,
        joints=ordered_joints,
        anchors=anchors,
        anchor_indices=anchor_indices,
        anchor_weights=anchor_weights,
        target_pixels=target_pixels,
        metric_support=metric_support,
        intrinsic=intrinsic,
        config=config,
    )
    aligned_vertices = apply_similarity(vertices, parameter)
    aligned_joints = apply_similarity(ordered_joints, parameter)
    aligned_anchors = aligned_joints[anchor_indices]
    projected_anchors = project_native(aligned_anchors, intrinsic)
    scale = float(np.exp(parameter[0]))
    rotation = rotation_matrix(parameter[1:4])
    transform = np.eye(4, dtype=np.float64)
    transform[:3, :3] = scale * rotation
    transform[:3, 3] = parameter[4:7]
    camera_vertices = aligned_vertices * np.asarray([1.0, -1.0, -1.0])
    positive_fraction = float(np.mean(camera_vertices[:, 2] > 0))
    anchor_nrmse = float(np.sqrt(np.mean(np.sum((aligned_anchors - anchors) ** 2, axis=1))) / fit["support_diagonal"])
    keypoint_nrmse = float(np.sqrt(np.mean(np.sum((projected_anchors - target_pixels) ** 2, axis=1))) / fit["visible_span_px"])
    sampled_vertices = deterministic_sample(aligned_vertices, int(config["surface_max_points"]), int(config["surface_sample_seed"]))
    sampled_support = deterministic_sample(metric_support, int(config["surface_max_points"]), int(config["surface_sample_seed"]) + 1)
    d1 = cKDTree(sampled_support).query(sampled_vertices, k=1, workers=1)[0]
    d2 = cKDTree(sampled_vertices).query(sampled_support, k=1, workers=1)[0]
    surface_nrmse = float(np.sqrt(np.mean(np.concatenate((d1, d2)) ** 2)) / fit["support_diagonal"])
    mask_fraction = projected_mask_fraction(aligned_vertices, intrinsic, hand_mask)
    lower_scale = float(np.exp(fit["lower"][0]))
    upper_scale = float(np.exp(fit["upper"][0]))
    margin = float(config["scale_bound_margin_fraction"])
    scale_saturated = bool(
        scale <= lower_scale * (1 + margin) or scale >= upper_scale * (1 - margin)
    )
    controls = {
        "proper_positive_sim3": bool(scale > 0 and np.linalg.det(rotation) > 0 and np.isfinite(transform).all()),
        "positive_camera_depth": positive_fraction >= float(config["minimum_positive_camera_depth_fraction"]),
        "keypoint_reprojection": keypoint_nrmse <= float(config["maximum_keypoint_nrmse"]),
        "metric_joint_anchors": anchor_nrmse <= float(config["maximum_anchor_nrmse"]),
        "symmetric_surface_support": surface_nrmse <= float(config["maximum_surface_nrmse"]),
        "selected_mask_support": mask_fraction >= float(config["minimum_projected_vertex_mask_fraction"]),
        "scale_not_saturated": not scale_saturated,
        "object_H2M_applied_to_hand": False,
    }
    passed = all(value is True for key, value in controls.items() if key != "object_H2M_applied_to_hand") and controls["object_H2M_applied_to_hand"] is False
    args.result_out.parent.mkdir(parents=True, exist_ok=True)
    with args.result_out.open("xb") as stream:
        np.savez_compressed(
            stream,
            hand_to_frame_i_4x4=transform,
            global_scale=np.asarray(scale),
            rotation_matrix_3x3=rotation,
            translation_xyz=parameter[4:7],
            aligned_vertices_moge_Nx3=aligned_vertices,
            aligned_joints_moge_21x3=aligned_joints,
            projected_keypoints_21x2=project_native(aligned_joints, intrinsic),
            positive_camera_depth_fraction=np.asarray(positive_fraction),
            proper_sim3=np.asarray(controls["proper_positive_sim3"]),
        )
    report = {
        "schema": "tracehoi.HandSpecificFrameIResult.v1",
        "decision": "hand_specific_frame_I_candidate_result_written" if passed else "hold_for_hand_specific_frame_I_candidate_result",
        "scale": scale,
        "rotation_matrix_3x3": rotation.tolist(),
        "translation_xyz": parameter[4:7].tolist(),
        "anchor_count": int(anchor_indices.size),
        "anchor_joint_indices": anchor_indices.tolist(),
        "anchor_nrmse": anchor_nrmse,
        "keypoint_nrmse": keypoint_nrmse,
        "surface_nrmse": surface_nrmse,
        "projected_vertex_mask_fraction": mask_fraction,
        "positive_camera_depth_fraction": positive_fraction,
        "scale_at_bound": scale_saturated,
        "projection_camera_owner": "native_moge_point_map",
        "projection_intrinsic_3x3": intrinsic.tolist(),
        "source_hamer_intrinsic_3x3": source_hamer_intrinsic.tolist(),
        "moge_intrinsic_recovery": intrinsic_recovery,
        "controls": controls,
        "solver_status": int(solver.status),
        "solver_cost": float(solver.cost),
        "solver_nfev": int(solver.nfev),
        "object_H2M_applied_to_hand": False,
        "optimized_variables": ["one_positive_hand_scale", "one_proper_SO3_root_rotation", "one_Frame_I_translation_xyz"],
        "frozen_variables": ["selected_hand_identity", "MANO_shape", "MANO_articulation", "MANO_topology", "Gate_A_object_geometry"],
        "inputs": {name: {"path": str(path), "sha256": sha256(path)} for name, (path, _) in inputs.items()},
        "result": str(args.result_out),
        "result_sha256": sha256(args.result_out),
        "authorizes_frame_i": False,
        "authorizes_installation": False,
        "authorizes_contact_optimization": False,
    }
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"decision": report["decision"], "controls": controls}, sort_keys=True))


if __name__ == "__main__":
    main()
