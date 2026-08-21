#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    required = (
        "expected_image_sha256",
        "vitpose_module_root",
        "device",
        "handedness",
        "visibility_confidence_threshold",
        "require_exactly_one_pose",
        "expected_image_size_wh",
    )
    missing = [key for key in required if key not in data or data[key] is None]
    if missing:
        raise ValueError(f"Target configuration is incomplete: {missing}")
    if data["handedness"] not in ("left", "right"):
        raise ValueError("handedness must be left or right")
    threshold = float(data["visibility_confidence_threshold"])
    if not np.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("visibility_confidence_threshold must lie in [0, 1]")
    if data["require_exactly_one_pose"] is not True:
        raise ValueError("require_exactly_one_pose must be true")
    expected_size = data["expected_image_size_wh"]
    if (not isinstance(expected_size, list) or len(expected_size) != 2
            or any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in expected_size)):
        raise ValueError("expected_image_size_wh must contain two positive integers")
    return data


def load_vitpose_model(module_root: Path, device: str):
    module_root = module_root.resolve()
    module_path = module_root / "vitpose_model.py"
    if not module_path.is_file():
        raise FileNotFoundError(f"ViTPose module source is absent: {module_path}")
    spec = importlib.util.spec_from_file_location("foho_runtime_vitpose_model", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the exact ViTPose module source")
    module = importlib.util.module_from_spec(spec)
    previous = Path.cwd()
    try:
        os.chdir(module_root)
        spec.loader.exec_module(module)
        model_type = getattr(module, "ViTPoseModel", None)
        if model_type is None:
            raise RuntimeError("vitpose_model.ViTPoseModel is unavailable")
        return model_type(device)
    finally:
        os.chdir(previous)


def extract_hand_keypoints(pose: dict[str, Any], handedness: str) -> np.ndarray:
    keypoints = np.asarray(pose.get("keypoints"), dtype=np.float64)
    if keypoints.ndim != 2 or keypoints.shape[0] < 42 or keypoints.shape[1] < 3:
        raise ValueError(f"Expected whole-body keypoints with at least 42x3 values, got {keypoints.shape}")
    hand = keypoints[-42:-21] if handedness == "left" else keypoints[-21:]
    if hand.shape != (21, keypoints.shape[1]) or not np.isfinite(hand[:, :3]).all():
        raise ValueError(f"Invalid selected hand keypoints: {hand.shape}")
    return hand


def write_new(path: Path, payload: bytes) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--target-out", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    args = parser.parse_args()

    config = load_config(args.config)
    if not args.image.is_file():
        raise FileNotFoundError(f"Full image does not exist: {args.image}")
    image_hash = sha256(args.image)
    if image_hash != config["expected_image_sha256"]:
        raise ValueError("Full-image hash does not match the frozen configuration")
    if args.target_out.exists() or args.report_out.exists():
        raise FileExistsError("Target or report output already exists")

    image = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unable to read image: {args.image}")
    height, width = image.shape[:2]
    expected_size = tuple(map(int, config["expected_image_size_wh"]))
    if (width, height) != expected_size:
        raise ValueError(f"Expected exact configured image size {expected_size}, got {(width, height)}")

    model = load_vitpose_model(Path(config["vitpose_module_root"]), str(config["device"]))
    full_frame_box = np.asarray([[0.0, 0.0, float(width - 1), float(height - 1), 1.0]], dtype=np.float32)
    poses = model.predict_pose(image, [full_frame_box])
    if not isinstance(poses, (list, tuple)) or len(poses) != 1:
        raise RuntimeError(f"Expected exactly one full-frame pose, got {len(poses) if hasattr(poses, '__len__') else None}")

    selected = extract_hand_keypoints(poses[0], str(config["handedness"]))
    xy = np.asarray(selected[:, :2], dtype=np.float64)
    confidence = np.asarray(selected[:, 2], dtype=np.float64)
    visibility = confidence >= float(config["visibility_confidence_threshold"])
    if xy.shape != (21, 2) or confidence.shape != (21,) or visibility.shape != (21,):
        raise ValueError("Target output shape contract failed")
    if not np.isfinite(xy).all() or not np.isfinite(confidence).all():
        raise ValueError("Target contains non-finite values")

    args.target_out.parent.mkdir(parents=True, exist_ok=True)
    with args.target_out.open("xb") as stream:
        np.savez_compressed(
            stream,
            keypoints_xy_full_image_px_21x2=xy,
            confidence_21=confidence,
            visibility_21=visibility,
            handedness=np.asarray(str(config["handedness"])),
            image_size_wh=np.asarray([width, height], dtype=np.int64),
        )
    report = {
        "schema": "independent_full_image_vitpose_target_v99_11_7_5",
        "decision": "pass_v99_11_7_5_independent_full_image_vitpose_target",
        "image": str(args.image),
        "image_sha256": image_hash,
        "image_size_wh": [width, height],
        "handedness": str(config["handedness"]),
        "visibility_confidence_threshold": float(config["visibility_confidence_threshold"]),
        "visible_joint_count": int(visibility.sum()),
        "target": str(args.target_out),
        "target_sha256": sha256(args.target_out),
        "source": str(Path(__file__).resolve()),
        "source_sha256": sha256(Path(__file__).resolve()),
        "candidate_projection_read": False,
        "authorizes_calibration": False,
        "authorizes_candidate_selection": False,
        "authorizes_v3": False,
        "authorizes_optimizer": False,
    }
    write_new(args.report_out, (json.dumps(report, indent=2) + "\n").encode())
    print(f"decision={report['decision']} visible={report['visible_joint_count']} target={args.target_out}")


if __name__ == "__main__":
    main()
