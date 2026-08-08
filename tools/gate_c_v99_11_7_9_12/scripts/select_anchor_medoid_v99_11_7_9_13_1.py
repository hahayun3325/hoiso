#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def scalar_from_path_or_text(raw: str) -> float:
    path = Path(raw)
    if path.is_file():
        arr = np.asarray(np.load(path), dtype=np.float64).reshape(-1)
        if arr.size != 1 or not np.isfinite(arr[0]):
            raise ValueError(f"normalization file must contain one finite scalar: {path}")
        return float(arr[0])
    value = float(raw)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("normalization must be finite and positive")
    return value


def load_manifest(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            uid = str(row.get("candidate_uid", "")).strip()
            if not uid:
                raise ValueError("manifest row missing candidate_uid")
            rows[uid] = row
    return rows


def f(row: dict[str, Any], name: str, default: float) -> float:
    raw = str(row.get(name, "")).strip()
    return default if raw == "" else float(raw)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("calibrate_v6", "apply_v3"), required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--identity-route", required=True)
    parser.add_argument("--normalization", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--frozen-dispersion-threshold", type=float)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    identity_path = Path(args.identity_route)
    policy_path = Path(args.policy)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not manifest_path.is_file() or not identity_path.is_file() or not policy_path.is_file():
        print("[HOLD] MISSING_MANIFEST_IDENTITY_OR_POLICY")
        return 0

    normalization = scalar_from_path_or_text(args.normalization)
    identity = json.loads(identity_path.read_text())
    valid = list(identity.get("identity_valid_survivors", []))
    manifest = load_manifest(manifest_path)

    missing = [uid for uid in valid if uid not in manifest]
    if missing:
        print(f"[HOLD] MANIFEST_MISSING_UIDS={missing}")
        return 0

    if len(valid) == 0:
        decision = "reject_all_no_identity_valid_survivor"
        selected = None
        scores: dict[str, float] = {}
        threshold = None
    elif len(valid) == 1:
        decision = "select_single_identity_valid_survivor"
        selected = valid[0]
        scores = {selected: 0.0}
        threshold = args.frozen_dispersion_threshold
    else:
        points: dict[str, np.ndarray] = {}
        for uid in valid:
            kp_path = Path(str(manifest[uid].get("keypoints_npy", "")))
            if not kp_path.is_file():
                print(f"[HOLD] KEYPOINTS_MISSING={uid}:{kp_path}")
                return 0
            arr = np.asarray(np.load(kp_path), dtype=np.float64)
            if arr.shape != (21, 2) or not np.isfinite(arr).all():
                print(f"[HOLD] KEYPOINTS_INVALID={uid}:shape={arr.shape}")
                return 0
            points[uid] = arr

        scores = {}
        for uid in valid:
            distances = []
            for other in valid:
                if uid == other:
                    continue
                diff = points[uid] - points[other]
                distances.append(float(np.sqrt(np.mean(np.sum(diff * diff, axis=1))) / normalization))
            scores[uid] = float(np.mean(distances))

        values = np.asarray(list(scores.values()), dtype=np.float64)
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        scaled_mad = 1.4826 * mad
        calibrated = float(median + 3.0 * scaled_mad)
        if mad == 0.0:
            calibrated = float(np.max(values) + 1e-12)

        if args.mode == "calibrate_v6":
            threshold = calibrated
        else:
            if args.frozen_dispersion_threshold is None:
                print("[HOLD] V3_REQUIRES_FROZEN_DISPERSION_THRESHOLD")
                return 0
            threshold = float(args.frozen_dispersion_threshold)

        def rank(uid: str) -> tuple[Any, ...]:
            row = manifest[uid]
            return (
                scores[uid],
                -f(row, "neighbor_crop_consensus_score", -math.inf),
                f(row, "full_image_keypoint_nrmse", math.inf),
                f(row, "normalized_metric_depth_residual", math.inf),
                uid,
            )

        selected = min(valid, key=rank)
        if scores[selected] <= threshold:
            decision = "select_one_medoid_anchor"
        else:
            decision = "reject_all_family_dispersion_exceeds_frozen_v6_threshold"
            selected = None

    packet = {
        "schema": "deterministic_anchor_consensus_result_v99_11_7_9_13",
        "mode": args.mode,
        "decision": decision,
        "selected_candidate_uid": selected,
        "identity_valid_survivors": valid,
        "normalization": normalization,
        "medoid_scores": scores,
        "dispersion_threshold": threshold,
        "tie_break_order": [
            "lower_medoid_score",
            "higher_neighbor_crop_consensus_score_defined_as_negative_frozen_distance",
            "lower_full_image_keypoint_nrmse",
            "lower_normalized_metric_depth_residual",
            "lexicographic_candidate_uid",
        ],
        "historical_s100_center_privileged": False,
        "authorizes_v3_execution": False,
        "authorizes_optimizer": False,
    }
    out = out_dir / "anchor_consensus_result.json"
    out.write_text(json.dumps(packet, indent=2) + "\n")
    print(f"[PASS] RESULT={out}")
    print(f"[INFO] DECISION={decision}")
    print(f"[INFO] SELECTED={selected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
