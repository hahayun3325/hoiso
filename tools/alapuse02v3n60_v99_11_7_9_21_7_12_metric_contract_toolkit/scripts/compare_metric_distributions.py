#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any

METRICS = (
    "positive_metric_depth_fraction",
    "normalized_metric_depth_residual",
    "full_image_keypoint_nrmse",
    "full_image_keypoint_np95",
    "neighbor_crop_consensus",
)


def summarize(values: list[float]) -> dict[str, Any] | None:
    finite = [float(v) for v in values if math.isfinite(float(v))]
    if not finite:
        return None
    med = statistics.median(finite)
    mad = statistics.median(abs(v - med) for v in finite)
    return {
        "count": len(finite),
        "minimum": min(finite),
        "maximum": max(finite),
        "mean": statistics.fmean(finite),
        "median": med,
        "mad": mad,
        "population_std": statistics.pstdev(finite) if len(finite) > 1 else 0.0,
        "range": max(finite) - min(finite),
        "unique_rounded_12": len({round(v, 12) for v in finite}),
        "candidate_invariant_to_1e_12": (max(finite) - min(finite)) <= 1e-12,
    }


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise TypeError(f"Expected JSON object in {path}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v6-table", type=Path, required=True)
    parser.add_argument("--v3-gate", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    v6 = load_json(args.v6_table)
    v3 = load_json(args.v3_gate)
    v6_rows = v6.get("candidates", [])
    v3_rows = v3.get("candidate_gate_results", [])
    if not isinstance(v6_rows, list) or not isinstance(v3_rows, list):
        raise TypeError("Unexpected candidate-table schema")

    result: dict[str, Any] = {
        "schema": "v6_v3_metric_distribution_comparison_v99_11_7_9_21_7_12",
        "v6_candidate_count": len(v6_rows),
        "v3_candidate_count": len(v3_rows),
        "metrics": {},
        "interpretation_policy": {
            "candidate_invariant_failure": (
                "family-level target/frame/binding effect is more likely than crop discrimination"
            ),
            "tight_failure_band": (
                "shared global alignment or gate-transfer effect should be investigated"
            ),
            "authorizes_threshold_change": False,
            "authorizes_optimizer": False,
        },
    }

    for metric in METRICS:
        v6_values: list[float] = []
        v3_values: list[float] = []
        threshold = None
        direction = None
        for row in v6_rows:
            value = row.get("metrics", {}).get(metric) if isinstance(row, dict) else None
            if value is not None:
                v6_values.append(float(value))
        for row in v3_rows:
            check = row.get("checks", {}).get(metric, {}) if isinstance(row, dict) else {}
            value = check.get("value") if isinstance(check, dict) else None
            if value is not None:
                v3_values.append(float(value))
            if threshold is None and isinstance(check, dict):
                threshold = check.get("threshold")
                direction = check.get("direction")
        result["metrics"][metric] = {
            "direction": direction,
            "frozen_v6_threshold": threshold,
            "v6_distribution": summarize(v6_values),
            "v3_distribution": summarize(v3_values),
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[PASS] OUT={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
