#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Tuple

import cv2
import numpy as np

from common import load_pickle_npy_dict, load_thresholds, passes_identity, point_metrics, sha256_file, to_numpy, write_json


def parser() -> Tuple[argparse.Namespace, list[str]]:
    p = argparse.ArgumentParser(description="Reproduce FollowMyHold saved guidance 2D keypoints from its 3D joints and camera.")
    p.add_argument("--guidance-npy", default="")
    p.add_argument("--image", default="")
    p.add_argument("--base-focal", default="5000.0")
    p.add_argument("--model-image-size", default="256.0")
    p.add_argument("--active-contract-json", default="")
    p.add_argument("--thresholds", default="")
    p.add_argument("--out-dir", default="")
    return p.parse_known_args()


def load_cfg_focal(args: argparse.Namespace) -> tuple[float, float]:
    base_focal = float(args.base_focal)
    model_size = float(args.model_image_size)
    if args.active_contract_json:
        data = json.loads(Path(args.active_contract_json).read_text(encoding="utf-8"))
        cfg = data.get("relevant_cfg", {})
        v = cfg.get("EXTRA.FOCAL_LENGTH")
        if isinstance(v, (int, float)):
            base_focal = float(v)
        v = cfg.get("MODEL.IMAGE_SIZE")
        if isinstance(v, (int, float)):
            model_size = float(v)
    return base_focal, model_size


def perspective(points: np.ndarray, translation: np.ndarray, focal: float, center: np.ndarray) -> np.ndarray:
    p = np.asarray(points, dtype=np.float64) + np.asarray(translation, dtype=np.float64).reshape(1, 3)
    z = p[:, 2:3]
    if np.any(np.abs(z) < 1e-12):
        raise ValueError("Projection contains near-zero depth")
    xy = p[:, :2] / z
    xy[:, 0] = xy[:, 0] * focal + center[0]
    xy[:, 1] = xy[:, 1] * focal + center[1]
    return xy


def main() -> int:
    args, unknown = parser()
    if unknown:
        print(f"[HOLD] Unknown arguments: {unknown}", file=sys.stderr)
        return 1
    if not args.guidance_npy or not args.image:
        print("[HOLD] --guidance-npy and --image are required", file=sys.stderr)
        return 1

    guidance_path = Path(args.guidance_npy).expanduser().resolve()
    image_path = Path(args.image).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else Path.cwd() / "H2_projection_identity"
    out_dir.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "status": "HOLD_H2_NOT_COMPLETED",
        "stage": "H2_projection_identity",
        "authorizes_mapping": False,
        "authorizes_mesh_movement": False,
    }
    try:
        if not guidance_path.is_file() or not image_path.is_file():
            raise FileNotFoundError(f"guidance={guidance_path.is_file()} image={image_path.is_file()}")
        d = load_pickle_npy_dict(guidance_path)
        needed = ["mano_3d_kps", "mano_2d_kps", "cam_t"]
        missing = [k for k in needed if k not in d]
        if missing:
            raise KeyError(f"Guidance file missing {missing}; available={sorted(d.keys())}")
        k3 = np.asarray(to_numpy(d["mano_3d_kps"]), dtype=np.float64)
        k2 = np.asarray(to_numpy(d["mano_2d_kps"]), dtype=np.float64)
        cam = np.asarray(to_numpy(d["cam_t"]), dtype=np.float64)
        while k3.ndim > 2 and k3.shape[0] == 1:
            k3 = k3[0]
        while k2.ndim > 2 and k2.shape[0] == 1:
            k2 = k2[0]
        cam = cam.reshape(-1, 3)[0]

        img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Could not read image: {image_path}")
        h, w = img.shape[:2]
        base_focal, model_size = load_cfg_focal(args)
        scaled_focal = base_focal / model_size * max(h, w)
        center = np.array([w / 2.0, h / 2.0], dtype=np.float64)
        reproj = perspective(k3, cam, scaled_focal, center)
        metrics = point_metrics(k2, reproj)
        thresholds = load_thresholds(args.thresholds or None)
        passed = passes_identity(metrics, thresholds["h2_max_abs_px"], thresholds["h2_rmse_px"])
        status = "PASS_H2_PROJECTION_IDENTITY" if passed else "HOLD_H2_PROJECTION_IDENTITY_FAILED"
        report.update(
            {
                "status": status,
                "pass": passed,
                "metrics": metrics,
                "image_size_hw": [h, w],
                "base_focal": base_focal,
                "model_image_size": model_size,
                "scaled_focal": scaled_focal,
                "camera_center": center.tolist(),
                "camera_translation": cam.tolist(),
                "thresholds": thresholds,
                "hashes": {"guidance_npy": sha256_file(guidance_path), "image": sha256_file(image_path)},
                "note": "This reproduces the official FollowMyHold full-image perspective projection. It does not test C1 or live-helper identity.",
            }
        )
        write_json(out_dir / "report.json", report)
        np.save(out_dir / "reprojected_2d.npy", reproj)
        np.save(out_dir / "saved_2d.npy", k2)
        print(f"[{ 'PASS' if passed else 'HOLD' }] {status}")
        print(out_dir / "report.json")
        return 0 if passed else 1
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()
        write_json(out_dir / "report.json", report)
        print(f"[HOLD] H2 projection audit failed: {exc}", file=sys.stderr)
        print(out_dir / "report.json", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
