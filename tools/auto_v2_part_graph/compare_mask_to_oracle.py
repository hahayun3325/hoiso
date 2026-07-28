#!/usr/bin/env python3
"""Compute evaluation-only mask IoU and boundary F1 against Candidate I oracle.

Usage:
  python3 compare_mask_to_oracle.py AUTO_MASK.png ORACLE_MASK.png OUTPUT.json [TOLERANCE_PX]

The oracle is used only as an evaluation label, never to construct the auto mask.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if len(sys.argv) not in (4, 5):
        print("[HOLD] MASK_METRIC_USAGE=AUTO_MASK.png ORACLE_MASK.png OUTPUT.json [TOLERANCE_PX]")
        return
    auto_path = Path(sys.argv[1])
    oracle_path = Path(sys.argv[2])
    out_path = Path(sys.argv[3])
    try:
        tolerance = int(sys.argv[4]) if len(sys.argv) == 5 else 3
    except ValueError:
        print("[HOLD] MASK_METRIC_TOLERANCE_INVALID")
        return
    if not auto_path.is_file() or not oracle_path.is_file():
        print(
            "[HOLD] MASK_METRIC_INPUT_MISSING="
            f"auto={auto_path.is_file()} oracle={oracle_path.is_file()}"
        )
        return
    if out_path.exists():
        print(f"[HOLD] MASK_METRIC_OUTPUT_EXISTS={out_path}")
        return
    try:
        import cv2
        import numpy as np
        from PIL import Image

        auto_img = Image.open(auto_path).convert("L")
        oracle_img = Image.open(oracle_path).convert("L")
        if auto_img.size != oracle_img.size:
            auto_img = auto_img.resize(oracle_img.size, Image.Resampling.NEAREST)
        auto = np.asarray(auto_img) >= 128
        oracle = np.asarray(oracle_img) >= 128
        intersection = int((auto & oracle).sum())
        union = int((auto | oracle).sum())
        auto_pixels = int(auto.sum())
        oracle_pixels = int(oracle.sum())
        iou = intersection / max(1, union)
        precision = intersection / max(1, auto_pixels)
        recall = intersection / max(1, oracle_pixels)

        kernel = np.ones((3, 3), np.uint8)
        auto_boundary = auto ^ (cv2.erode(auto.astype(np.uint8), kernel, iterations=1) > 0)
        oracle_boundary = oracle ^ (cv2.erode(oracle.astype(np.uint8), kernel, iterations=1) > 0)
        auto_dist = cv2.distanceTransform((~auto_boundary).astype(np.uint8), cv2.DIST_L2, 3)
        oracle_dist = cv2.distanceTransform((~oracle_boundary).astype(np.uint8), cv2.DIST_L2, 3)
        auto_match = int((auto_boundary & (oracle_dist <= tolerance)).sum())
        oracle_match = int((oracle_boundary & (auto_dist <= tolerance)).sum())
        b_precision = auto_match / max(1, int(auto_boundary.sum()))
        b_recall = oracle_match / max(1, int(oracle_boundary.sum()))
        boundary_f1 = 2 * b_precision * b_recall / max(1e-12, b_precision + b_recall)

        record = {
            "schema_version": "auto_vs_oracle_mask_metrics_v1",
            "auto_mask": str(auto_path),
            "auto_mask_sha256": digest(auto_path),
            "oracle_mask": str(oracle_path),
            "oracle_mask_sha256": digest(oracle_path),
            "oracle_use": "evaluation_only",
            "iou": iou,
            "precision": precision,
            "recall": recall,
            "boundary_tolerance_px": tolerance,
            "boundary_precision": b_precision,
            "boundary_recall": b_recall,
            "boundary_f1": boundary_f1,
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"[PASS] MASK_METRICS={out_path}")
        print(f"[INFO] MASK_IOU={iou:.6f}")
        print(f"[INFO] MASK_BOUNDARY_F1={boundary_f1:.6f}")
    except Exception as error:
        print(f"[HOLD] MASK_METRIC_FAILED={type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
