#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

TRUE = {"1", "true", "yes", "pass", "y"}


def as_bool(value: str) -> bool:
    return str(value).strip().lower() in TRUE


def load_kps(path: Path) -> np.ndarray:
    arr = np.asarray(np.load(path), dtype=np.float64)
    if arr.shape != (21, 2):
        raise ValueError(f"Expected 21x2 keypoints at {path}, got {arr.shape}")
    if not np.isfinite(arr).all():
        raise ValueError(f"Non-finite keypoints at {path}")
    return arr


def load_weights(path: Path | None) -> np.ndarray:
    if path is None:
        return np.ones(21, dtype=np.float64)
    w = np.asarray(np.load(path), dtype=np.float64).reshape(-1)
    if w.shape != (21,):
        raise ValueError(f"Expected 21 weights, got {w.shape}")
    if not np.isfinite(w).all() or np.any(w < 0) or float(w.sum()) <= 0:
        raise ValueError("Weights must be finite, non-negative, and nonzero")
    return w


def mask_iou(a_path: Path, b_path: Path) -> float:
    a = np.asarray(Image.open(a_path).convert("L")) > 0
    b = np.asarray(Image.open(b_path).convert("L")) > 0
    if a.shape != b.shape:
        raise ValueError(f"Mask shape mismatch: {a.shape} vs {b.shape}")
    union = np.logical_or(a, b).sum()
    if union == 0:
        return 1.0
    return float(np.logical_and(a, b).sum() / union)


def percentile_weighted(errors: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(errors)
    e = errors[order]
    w = weights[order]
    c = np.cumsum(w) / w.sum()
    idx = int(np.searchsorted(c, q, side="left"))
    return float(e[min(idx, len(e) - 1)])


def require_thresholds(policy: dict[str, Any]) -> None:
    for key in ("max_normalized_rmse", "max_normalized_p95"):
        if policy.get(key) is None:
            raise ValueError(f"Policy field {key} is null; calibrate/freeze on v6 first")
    if policy.get("require_silhouette") and policy.get("min_silhouette_iou") is None:
        raise ValueError("min_silhouette_iou is null while silhouette is required")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--target-kps", type=Path, required=True)
    p.add_argument("--normalization", type=float, required=True)
    p.add_argument("--policy", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--weights", type=Path)
    p.add_argument("--target-mask", type=Path)
    args = p.parse_args()

    policy = json.loads(args.policy.read_text())
    require_thresholds(policy)
    if not math.isfinite(args.normalization) or args.normalization <= 0:
        raise ValueError("Normalization must be a positive finite scalar")

    target = load_kps(args.target_kps)
    weights = load_weights(args.weights)

    rows = list(csv.DictReader(args.manifest.open(newline="")))
    results: list[dict[str, Any]] = []
    for row in rows:
        uid = row.get("candidate_uid", "").strip()
        if not uid:
            continue
        result: dict[str, Any] = {"candidate_uid": uid}
        try:
            pred = load_kps(Path(row["projected_kps_path"]))
            err = np.linalg.norm(pred - target, axis=1)
            rmse = float(np.sqrt(np.sum(weights * err**2) / np.sum(weights)))
            p95 = percentile_weighted(err, weights, 0.95)
            nrmse = rmse / args.normalization
            np95 = p95 / args.normalization

            iou: float | None = None
            cand_mask = row.get("candidate_mask_path", "").strip()
            if args.target_mask and cand_mask:
                iou = mask_iou(args.target_mask, Path(cand_mask))

            hard = {
                "provenance": as_bool(row.get("provenance_pass", "")),
                "handedness": as_bool(row.get("handedness_pass", "")),
                "crop_raster": as_bool(row.get("crop_raster_pass", "")),
                "physical_upper_hand": as_bool(row.get("physical_upper_hand_pass", "")),
                "positive_depth": as_bool(row.get("positive_depth_pass", "")),
            }
            checks = [
                (not policy.get("require_provenance", True)) or hard["provenance"],
                (not policy.get("require_handedness", True)) or hard["handedness"],
                (not policy.get("require_crop_raster", True)) or hard["crop_raster"],
                (not policy.get("require_physical_upper_hand", True)) or hard["physical_upper_hand"],
                (not policy.get("require_positive_depth", True)) or hard["positive_depth"],
                nrmse <= float(policy["max_normalized_rmse"]),
                np95 <= float(policy["max_normalized_p95"]),
            ]
            if policy.get("require_silhouette"):
                checks.append(iou is not None and iou >= float(policy["min_silhouette_iou"]))

            result.update({
                "weighted_rmse_px": rmse,
                "weighted_p95_px": p95,
                "normalized_rmse": nrmse,
                "normalized_p95": np95,
                "silhouette_iou": iou,
                "hard_gates": hard,
                "gate_pass": bool(all(checks)),
                "notes": row.get("notes", ""),
            })
        except Exception as exc:
            result.update({"gate_pass": False, "error": f"{type(exc).__name__}: {exc}"})
        results.append(result)

    results.sort(key=lambda r: (
        not bool(r.get("gate_pass")),
        float(r.get("normalized_rmse", float("inf"))),
        float(r.get("normalized_p95", float("inf"))),
        -float(r.get("silhouette_iou") if r.get("silhouette_iou") is not None else -1.0),
    ))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "candidate_zero_state_metrics_v99_12",
        "target_kps": str(args.target_kps),
        "target_mask": str(args.target_mask) if args.target_mask else None,
        "normalization": args.normalization,
        "policy": policy,
        "results": results,
        "authorizes_optimizer": False,
    }
    (args.out_dir / "candidate_zero_state_metrics_v99_12.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )

    fields = [
        "candidate_uid", "gate_pass", "normalized_rmse", "normalized_p95",
        "weighted_rmse_px", "weighted_p95_px", "silhouette_iou", "error", "notes"
    ]
    with (args.out_dir / "candidate_zero_state_metrics_v99_12.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k) for k in fields})
    print(f"[PASS] RESULTS={len(results)} OUT={args.out_dir}")


if __name__ == "__main__":
    main()
