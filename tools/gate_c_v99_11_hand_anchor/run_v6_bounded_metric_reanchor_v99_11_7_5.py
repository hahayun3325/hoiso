#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    required = (
        "expected_candidate_sha256",
        "expected_target_sha256",
        "expected_H2M_sha256",
        "expected_points_sha256",
        "expected_hand_mask_sha256",
        "packet_fields",
        "joint_map_21",
        "positive_scale_bounds",
        "translation_lower_xyz",
        "translation_upper_xyz",
        "metric_point_to_surface_weight",
        "metric_residual_clip",
        "metric_max_points",
        "metric_sample_seed",
        "minimum_visible_joints",
        "PnP_max_initializer_rotation_radians",
        "PnP_max_final_reprojection_rmse_px",
        "six_v6_gate_thresholds",
    )
    missing = [key for key in required if key not in data]
    null_operational = [key for key in required if key != "six_v6_gate_thresholds" and data.get(key) is None]
    if missing or null_operational:
        raise ValueError(f"Reanchor configuration is incomplete: missing={missing} null={null_operational}")
    if data["six_v6_gate_thresholds"] is not None:
        raise ValueError("six_v6_gate_thresholds must remain null during v6 calibration")
    fields = data["packet_fields"]
    if set(fields) != {"vertices", "joints_3d", "focal_length", "camera_translation"} or any(not fields[key] for key in fields):
        raise ValueError("packet_fields must bind vertices, joints_3d, focal_length, and camera_translation")
    joint_map = np.asarray(data["joint_map_21"], dtype=np.int64)
    if joint_map.shape != (21,) or sorted(joint_map.tolist()) != list(range(21)):
        raise ValueError("joint_map_21 must be a permutation of 0..20")
    scale_bounds = np.asarray(data["positive_scale_bounds"], dtype=np.float64)
    lower = np.asarray(data["translation_lower_xyz"], dtype=np.float64)
    upper = np.asarray(data["translation_upper_xyz"], dtype=np.float64)
    if scale_bounds.shape != (2,) or not 0.0 < scale_bounds[0] < scale_bounds[1]:
        raise ValueError("positive_scale_bounds must be two increasing positive values")
    if lower.shape != (3,) or upper.shape != (3,) or not np.all(lower < upper):
        raise ValueError("translation bounds must be two ordered xyz vectors")
    numeric_positive = (
        "metric_point_to_surface_weight",
        "metric_residual_clip",
        "metric_max_points",
        "minimum_visible_joints",
        "PnP_max_initializer_rotation_radians",
        "PnP_max_final_reprojection_rmse_px",
    )
    if any(not math.isfinite(float(data[key])) or float(data[key]) <= 0 for key in numeric_positive):
        raise ValueError("Operational numeric rules must be finite and positive")
    return data


def load_packet(path: Path) -> dict[str, Any]:
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
    array = np.asarray(value, dtype=np.float64)
    while array.ndim > 2 and array.shape[0] == 1:
        array = array[0]
    if array.ndim != 2 or array.shape[1] != 3 or array.shape[0] < minimum:
        raise ValueError(f"{name} must be Nx3 with N >= {minimum}, got {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains non-finite values")
    return array


def factor_similarity(matrix: np.ndarray) -> tuple[float, np.ndarray, np.ndarray, dict[str, float]]:
    if matrix.shape != (4, 4) or not np.isfinite(matrix).all() or not np.allclose(matrix[3], [0.0, 0.0, 0.0, 1.0], atol=1e-6):
        raise ValueError("H2M must be one finite homogeneous 4x4 matrix")
    linear = matrix[:3, :3]
    u, singular_values, vt = np.linalg.svd(linear)
    rotation = u @ vt
    if np.linalg.det(rotation) < 0:
        u[:, -1] *= -1.0
        rotation = u @ vt
    scale = float(np.mean(singular_values))
    spread = float((singular_values.max() - singular_values.min()) / scale)
    reconstruction = float(np.linalg.norm(linear - scale * rotation) / np.linalg.norm(linear))
    if spread > 1e-4 or reconstruction > 1e-4 or np.linalg.det(rotation) <= 0:
        raise ValueError("H2M linear block is not the frozen uniform proper similarity")
    return scale, rotation, matrix[:3, 3].copy(), {"relative_singular_spread": spread, "relative_reconstruction_error": reconstruction}


def apply_similarity(points: np.ndarray, scale: float, rotation: np.ndarray, translation: np.ndarray) -> np.ndarray:
    return scale * (points @ rotation.T) + translation.reshape(1, 3)


def load_metric_hand_points(points_path: Path, mask_path: Path, maximum: int, seed: int) -> np.ndarray:
    points = cv2.imread(str(points_path), cv2.IMREAD_UNCHANGED)
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if points is None or mask is None:
        raise ValueError("Unable to read MoGe points or hand mask")
    points = np.asarray(points, dtype=np.float64)
    mask = np.asarray(mask) > 0
    if points.ndim != 3 or points.shape[:2] != mask.shape or points.shape[2] < 3:
        raise ValueError(f"MoGe points/mask shape mismatch: points={points.shape} mask={mask.shape}")
    selected = points[..., :3][mask]
    selected = selected[np.isfinite(selected).all(axis=1)]
    if selected.shape[0] < 21:
        raise ValueError("Fewer than 21 finite metric hand points remain")
    if selected.shape[0] > maximum:
        rng = np.random.default_rng(seed)
        selected = selected[np.sort(rng.choice(selected.shape[0], size=maximum, replace=False))]
    return selected


def fit_relative_scale(vertices_moge: np.ndarray, pivot_moge: np.ndarray, metric_points: np.ndarray, config: dict[str, Any]):
    tree = cKDTree(metric_points)
    weight = float(config["metric_point_to_surface_weight"])
    clip = float(config["metric_residual_clip"])
    bounds = np.asarray(config["positive_scale_bounds"], dtype=np.float64)

    def residual(parameter: np.ndarray) -> np.ndarray:
        scaled = pivot_moge + float(parameter[0]) * (vertices_moge - pivot_moge)
        distances, _ = tree.query(scaled, k=1, workers=1)
        return weight * np.minimum(np.asarray(distances, dtype=np.float64), clip)

    initial = float(np.clip(1.0, bounds[0], bounds[1]))
    result = optimize.least_squares(
        residual,
        x0=np.asarray([initial], dtype=np.float64),
        bounds=(np.asarray([bounds[0]]), np.asarray([bounds[1]])),
        method="trf",
        jac="2-point",
    )
    if not result.success or not np.isfinite(result.x).all() or not np.isfinite(result.fun).all():
        raise RuntimeError(f"Bounded scale fit failed: status={result.status} message={result.message}")
    return float(result.x[0]), result


def camera_matrix(focal: Any, image_size_wh: np.ndarray) -> np.ndarray:
    values = np.asarray(focal, dtype=np.float64).reshape(-1)
    if values.size == 1:
        fx = fy = float(values[0])
    elif values.size >= 2:
        fx, fy = map(float, values[:2])
    else:
        raise ValueError("focal_length is empty")
    width, height = map(float, image_size_wh)
    if not all(math.isfinite(value) and value > 0 for value in (fx, fy, width, height)):
        raise ValueError("Invalid focal length or image dimensions")
    return np.asarray([[fx, 0.0, width / 2.0], [0.0, fy, height / 2.0], [0.0, 0.0, 1.0]], dtype=np.float64)


def project_fixed(points: np.ndarray, translation: np.ndarray, intrinsic: np.ndarray) -> np.ndarray:
    camera_points = points + translation.reshape(1, 3)
    if np.any(camera_points[:, 2] <= 0):
        return np.full((points.shape[0], 2), 1e9, dtype=np.float64)
    homogeneous = camera_points @ intrinsic.T
    return homogeneous[:, :2] / homogeneous[:, 2:3]


def fit_translation_only(points: np.ndarray, target_xy: np.ndarray, visibility: np.ndarray, intrinsic: np.ndarray, packet_translation: np.ndarray, config: dict[str, Any]):
    object_points = np.asarray(points[visibility], dtype=np.float64)
    image_points = np.asarray(target_xy[visibility], dtype=np.float64)
    if object_points.shape[0] < int(config["minimum_visible_joints"]):
        raise ValueError("Too few visible joints for translation fit")
    ok, rvec, tvec = cv2.solvePnP(
        object_points,
        image_points,
        intrinsic,
        np.zeros(5, dtype=np.float64),
        flags=cv2.SOLVEPNP_EPNP,
    )
    if not ok or not np.isfinite(rvec).all() or not np.isfinite(tvec).all():
        raise RuntimeError("OpenCV PnP initializer failed")
    rotation_magnitude = float(np.linalg.norm(rvec))
    if rotation_magnitude > float(config["PnP_max_initializer_rotation_radians"]):
        raise ValueError(f"PnP initializer requires excessive rotation: {rotation_magnitude}")
    lower = np.asarray(config["translation_lower_xyz"], dtype=np.float64)
    upper = np.asarray(config["translation_upper_xyz"], dtype=np.float64)
    initial_candidates = [np.asarray(tvec, dtype=np.float64).reshape(3), np.asarray(packet_translation, dtype=np.float64).reshape(3)]
    valid_initial = [np.clip(item, lower, upper) for item in initial_candidates if np.isfinite(item).all()]
    if not valid_initial:
        raise ValueError("No finite translation initializer is available")

    def residual(translation: np.ndarray) -> np.ndarray:
        return (project_fixed(object_points, translation, intrinsic) - image_points).reshape(-1)

    ranked = sorted(valid_initial, key=lambda item: float(np.mean(residual(item) ** 2)))
    result = optimize.least_squares(residual, x0=ranked[0], bounds=(lower, upper), method="trf", jac="2-point")
    if not result.success or not np.isfinite(result.x).all() or not np.isfinite(result.fun).all():
        raise RuntimeError(f"Translation-only fit failed: status={result.status} message={result.message}")
    rmse = float(np.sqrt(np.mean(result.fun ** 2)))
    if rmse > float(config["PnP_max_final_reprojection_rmse_px"]):
        raise ValueError(f"Translation-only reprojection RMSE exceeds the frozen tolerance: {rmse}")
    return np.asarray(result.x, dtype=np.float64), rotation_magnitude, rmse, result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--H2M", type=Path, required=True)
    parser.add_argument("--moge-points", type=Path, required=True)
    parser.add_argument("--hand-mask", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--result-out", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    inputs = {
        "candidate": (args.candidate, config["expected_candidate_sha256"]),
        "target": (args.target, config["expected_target_sha256"]),
        "H2M": (args.H2M, config["expected_H2M_sha256"]),
        "moge_points": (args.moge_points, config["expected_points_sha256"]),
        "hand_mask": (args.hand_mask, config["expected_hand_mask_sha256"]),
    }
    for name, (path, expected_hash) in inputs.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing {name}: {path}")
        if sha256(path) != expected_hash:
            raise ValueError(f"Hash mismatch for {name}")
    if args.result_out.exists() or args.report_out.exists():
        raise FileExistsError("Result or report output already exists")

    packet = load_packet(args.candidate)
    fields = config["packet_fields"]
    vertices = as_points(resolve_field(packet, fields["vertices"]), "vertices", 100)
    joints = as_points(resolve_field(packet, fields["joints_3d"]), "joints_3d", 21)
    if joints.shape[0] != 21:
        raise ValueError(f"Expected exactly 21 joints, got {joints.shape}")
    focal = resolve_field(packet, fields["focal_length"])
    packet_translation = np.asarray(resolve_field(packet, fields["camera_translation"]), dtype=np.float64).reshape(-1)
    if packet_translation.size != 3 or not np.isfinite(packet_translation).all():
        raise ValueError("Packet camera translation must contain three finite values")

    target = np.load(args.target, allow_pickle=False)
    target_xy = np.asarray(target["keypoints_xy_full_image_px_21x2"], dtype=np.float64)
    visibility = np.asarray(target["visibility_21"], dtype=bool)
    image_size_wh = np.asarray(target["image_size_wh"], dtype=np.int64)
    if target_xy.shape != (21, 2) or visibility.shape != (21,) or image_size_wh.shape != (2,):
        raise ValueError("Independent target shape contract failed")

    matrix = np.asarray(np.load(args.H2M), dtype=np.float64)
    h2m_scale, h2m_rotation, h2m_translation, h2m_facts = factor_similarity(matrix)
    vertices_moge = apply_similarity(vertices, h2m_scale, h2m_rotation, h2m_translation)
    joints_moge = apply_similarity(joints, h2m_scale, h2m_rotation, h2m_translation)
    pivot_moge = joints_moge[0]
    metric_points = load_metric_hand_points(args.moge_points, args.hand_mask, int(config["metric_max_points"]), int(config["metric_sample_seed"]))
    relative_scale, scale_result = fit_relative_scale(vertices_moge, pivot_moge, metric_points, config)

    joint_map = np.asarray(config["joint_map_21"], dtype=np.int64)
    ordered_joints = joints[joint_map]
    fixed_oriented_joints = relative_scale * (ordered_joints - ordered_joints[0])
    intrinsic = camera_matrix(focal, image_size_wh)
    translation, pnp_rotation_magnitude, reprojection_rmse, translation_result = fit_translation_only(
        fixed_oriented_joints,
        target_xy,
        visibility,
        intrinsic,
        packet_translation,
        config,
    )
    final_camera_points = fixed_oriented_joints + translation.reshape(1, 3)
    positive_depth_fraction = float(np.mean(final_camera_points[:, 2] > 0))

    args.result_out.parent.mkdir(parents=True, exist_ok=True)
    with args.result_out.open("xb") as stream:
        np.savez_compressed(
            stream,
            relative_metric_scale=np.asarray(relative_scale, dtype=np.float64),
            translation_xyz=np.asarray(translation, dtype=np.float64),
            intrinsic_3x3=intrinsic,
            fixed_oriented_joints_21x3=fixed_oriented_joints,
            projected_keypoints_21x2=project_fixed(fixed_oriented_joints, translation, intrinsic),
            positive_depth_fraction=np.asarray(positive_depth_fraction, dtype=np.float64),
        )
    report = {
        "schema": "bounded_metric_reanchor_result_v99_11_7_5",
        "decision": "pass_v99_11_7_5_bounded_metric_reanchor_raw_result",
        "relative_metric_scale": relative_scale,
        "scale_at_lower_bound": bool(np.isclose(relative_scale, float(config["positive_scale_bounds"][0]))),
        "scale_at_upper_bound": bool(np.isclose(relative_scale, float(config["positive_scale_bounds"][1]))),
        "scale_solver_status": int(scale_result.status),
        "scale_solver_cost": float(scale_result.cost),
        "translation_xyz": translation.tolist(),
        "translation_solver_status": int(translation_result.status),
        "PnP_initializer_rotation_radians": pnp_rotation_magnitude,
        "full_image_reprojection_rmse_px": reprojection_rmse,
        "positive_metric_depth_fraction": positive_depth_fraction,
        "H2M_factored_scale": h2m_scale,
        "H2M_facts": h2m_facts,
        "frozen_variables": ["MANO_pose", "MANO_shape", "root_rotation", "candidate_identity"],
        "optimized_variables": ["one_positive_relative_metric_scale", "translation_xyz"],
        "inputs": {name: {"path": str(path), "sha256": sha256(path)} for name, (path, _) in inputs.items()},
        "result": str(args.result_out),
        "result_sha256": sha256(args.result_out),
        "source": str(Path(__file__).resolve()),
        "source_sha256": sha256(Path(__file__).resolve()),
        "six_v6_gate_thresholds_applied": False,
        "authorizes_candidate_selection": False,
        "authorizes_v3": False,
        "authorizes_optimizer": False,
    }
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"decision={report['decision']} scale={relative_scale} reprojection_rmse_px={reprojection_rmse}")


if __name__ == "__main__":
    main()
