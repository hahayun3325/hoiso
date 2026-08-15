#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np


def load_array(path: Path) -> np.ndarray:
    return np.asarray(np.load(path), dtype=np.float64)


def select_scale(array: np.ndarray, scale_index: int, expected_tail: tuple[int, ...]) -> np.ndarray:
    if array.shape == expected_tail:
        return array
    if array.ndim == len(expected_tail) + 1 and array.shape[1:] == expected_tail:
        return array[scale_index]
    raise ValueError(f"unsupported shape {array.shape}; expected {expected_tail} or (S,{','.join(map(str, expected_tail))})")


def normalize_jacobian(array: np.ndarray, scale_index: int) -> np.ndarray:
    if array.ndim == 3:
        array = array[scale_index]
    if array.shape == (42, 21):
        return array
    if array.shape == (21, 42):
        return array.T
    raise ValueError(f"unsupported Jacobian shape {array.shape}; expected (42,21), (21,42), or scaled variants")


def expand_weights(raw: np.ndarray | None) -> np.ndarray:
    if raw is None:
        return np.ones(42, dtype=np.float64)
    raw = np.asarray(raw, dtype=np.float64).reshape(-1)
    if raw.size == 21:
        return np.repeat(raw, 2)
    if raw.size == 42:
        return raw
    raise ValueError(f"weights must contain 21 or 42 entries, got {raw.size}")


def weighted_norm(vector: np.ndarray, weights: np.ndarray) -> float:
    return float(np.sqrt(np.sum(weights * vector * vector)))


def residual_metrics(residual_21x2: np.ndarray, normalization: float | None = None) -> dict[str, float]:
    per_joint = np.linalg.norm(residual_21x2, axis=1)
    result = {
        "coordinate_rmse_px": float(np.sqrt(np.mean(residual_21x2 ** 2))),
        "joint_l2_mean_px": float(per_joint.mean()),
        "joint_l2_p95_px": float(np.percentile(per_joint, 95)),
        "joint_l2_max_px": float(per_joint.max()),
    }
    if normalization is not None and normalization > 0:
        result["normalized_coordinate_rmse"] = result["coordinate_rmse_px"] / normalization
        result["normalized_joint_l2_p95"] = result["joint_l2_p95_px"] / normalization
    return result


def fit_radial_tangential(points: np.ndarray, residual: np.ndarray, weights_21: np.ndarray) -> dict[str, Any]:
    origin = points[0]
    rel = points - origin
    radial = rel.reshape(-1)
    tangential = np.stack([-rel[:, 1], rel[:, 0]], axis=1).reshape(-1)
    tx = np.tile([1.0, 0.0], 21)
    ty = np.tile([0.0, 1.0], 21)
    basis = np.column_stack([tx, ty, radial, tangential])
    y = residual.reshape(-1)
    w = np.repeat(weights_21, 2)
    sw = np.sqrt(np.clip(w, 0.0, None))
    bw = sw[:, None] * basis
    yw = sw * y
    coefficients, *_ = np.linalg.lstsq(bw, yw, rcond=None)
    fitted = basis @ coefficients
    total = float(np.sum(w * y * y))
    unexplained = float(np.sum(w * (y - fitted) ** 2))
    overall_r2 = 0.0 if total <= 0 else max(0.0, 1.0 - unexplained / total)

    def one_component_r2(column: np.ndarray) -> float:
        cw = sw * column
        denom = float(cw @ cw)
        if denom <= 0 or total <= 0:
            return 0.0
        alpha = float((cw @ yw) / denom)
        err = float(np.sum((yw - alpha * cw) ** 2))
        return max(0.0, 1.0 - err / total)

    return {
        "translation_xy": coefficients[:2].tolist(),
        "radial_coefficient": float(coefficients[2]),
        "tangential_coefficient": float(coefficients[3]),
        "joint_similarity_r2": overall_r2,
        "radial_only_r2": one_component_r2(radial),
        "tangential_only_r2": one_component_r2(tangential),
        "note": "2D morphology heuristic only; it selects a derivative family but does not prove 3D root rotation or scale."
    }


def group_energy(residual: np.ndarray, groups: dict[str, list[int]], weights_21: np.ndarray) -> dict[str, float]:
    energy_by_group: dict[str, float] = {}
    total = 0.0
    for name, indices in groups.items():
        value = float(sum(weights_21[i] * float(residual[i] @ residual[i]) for i in indices))
        energy_by_group[name] = value
        total += value
    if total > 0:
        return {name: value / total for name, value in energy_by_group.items()}
    return {name: 0.0 for name in energy_by_group}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True)
    parser.add_argument("--zero", required=True)
    parser.add_argument("--bounded-predicted", required=True)
    parser.add_argument("--bounded-deltas", required=True)
    parser.add_argument("--jacobians", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--weights")
    parser.add_argument("--identity-weights-confirmed", action="store_true")
    parser.add_argument("--normalization")
    parser.add_argument("--scale-index", type=int)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    if args.weights and args.identity_weights_confirmed:
        raise ValueError("pass either --weights or --identity-weights-confirmed, not both")
    if not args.weights and not args.identity_weights_confirmed:
        raise ValueError("bind exact source weights or explicitly confirm identity weighting")

    policy = json.loads(Path(args.policy).read_text())
    scale_index = policy.get("primary_scale_index", 1) if args.scale_index is None else args.scale_index
    names = policy["joint_names"]
    groups = policy["finger_groups"]

    target = select_scale(load_array(Path(args.target)), scale_index, (21, 2))
    zero = select_scale(load_array(Path(args.zero)), scale_index, (21, 2))
    bounded = select_scale(load_array(Path(args.bounded_predicted)), scale_index, (21, 2))
    deltas_raw = load_array(Path(args.bounded_deltas))
    deltas = deltas_raw if deltas_raw.shape == (21,) else deltas_raw[scale_index]
    if deltas.shape != (21,):
        raise ValueError(f"bounded deltas must have 21 columns, got {deltas.shape}")
    jacobian = normalize_jacobian(load_array(Path(args.jacobians)), scale_index)

    raw_weights = None if args.identity_weights_confirmed else load_array(Path(args.weights))
    weights_42 = expand_weights(raw_weights)
    weights_21 = 0.5 * (weights_42[0::2] + weights_42[1::2])
    normalization = None
    if args.normalization:
        normalization_array = load_array(Path(args.normalization)).reshape(-1)
        normalization = float(normalization_array[0])

    r0 = (target - zero).reshape(-1)
    rb = (target - bounded).reshape(-1)
    sw = np.sqrt(np.clip(weights_42, 0.0, None))
    jw = sw[:, None] * jacobian
    rw = sw * r0
    x_unbounded, *_ = np.linalg.lstsq(jw, rw, rcond=None)
    unbounded_predicted = zero.reshape(-1) + jacobian @ x_unbounded
    ru = target.reshape(-1) - unbounded_predicted

    zero_norm = weighted_norm(r0, weights_42)
    bounded_norm = weighted_norm(rb, weights_42)
    unbounded_norm = weighted_norm(ru, weights_42)
    gap_norm = weighted_norm(rb - ru, weights_42)

    bounded_residual = rb.reshape(21, 2)
    unbounded_residual = ru.reshape(21, 2)
    zero_residual = r0.reshape(21, 2)

    morphology = fit_radial_tangential(
        unbounded_predicted.reshape(21, 2),
        unbounded_residual,
        weights_21,
    )
    unbounded_group = group_energy(unbounded_residual, groups, weights_21)
    bounded_group = group_energy(bounded_residual, groups, weights_21)

    report: dict[str, Any] = {
        "schema": "v88_residual_geometry_audit",
        "scale_index": scale_index,
        "weighting": "identity_source_confirmed" if args.identity_weights_confirmed else str(args.weights),
        "input_shapes": {
            "target": list(target.shape),
            "zero": list(zero.shape),
            "bounded_predicted": list(bounded.shape),
            "bounded_deltas": list(deltas.shape),
            "jacobian": list(jacobian.shape),
        },
        "weighted_residual_ratios": {
            "zero": 1.0,
            "bounded": None if zero_norm == 0 else bounded_norm / zero_norm,
            "unbounded_span_floor": None if zero_norm == 0 else unbounded_norm / zero_norm,
            "bounded_minus_unbounded_gap": None if zero_norm == 0 else gap_norm / zero_norm,
        },
        "residual_metrics": {
            "zero": residual_metrics(zero_residual, normalization),
            "bounded": residual_metrics(bounded_residual, normalization),
            "unbounded_span_floor": residual_metrics(unbounded_residual, normalization),
        },
        "unbounded_solution": {
            "parameter_vector": x_unbounded.tolist(),
            "translation_norm_in_registered_coordinates": float(np.linalg.norm(x_unbounded[:3])),
            "maximum_absolute_articulation_coordinate": float(np.max(np.abs(x_unbounded[3:]))),
        },
        "registered_bounded_solution": {
            "translation_norm_fraction": float(np.linalg.norm(deltas[:3])),
            "maximum_absolute_articulation_fraction": float(np.max(np.abs(deltas[3:]))),
            "articulation_absolute_bound_count": int(np.count_nonzero(np.isclose(np.abs(deltas[3:]), 1.0, atol=1e-6))),
        },
        "orthogonal_residual_morphology": morphology,
        "group_energy_fraction": {
            "bounded": bounded_group,
            "unbounded_span_floor": unbounded_group,
        },
        "interpretation": {
            "important": "High subspace coverage plus a large bounded/unbounded gap indicates a bound or local-linearization problem, not automatically a missing mode.",
            "authorizes_new_family": False,
            "authorizes_optimizer": False,
        },
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "unbounded_linear_solution_v88.npy", x_unbounded)
    np.save(out_dir / "unbounded_predicted_keypoints_v88.npy", unbounded_predicted.reshape(21, 2))
    (out_dir / "residual_geometry_report_v88.json").write_text(json.dumps(report, indent=2) + "\n")

    rows: list[dict[str, Any]] = []
    for index, name in enumerate(names):
        rows.append({
            "joint_index": index,
            "joint_name": name,
            "zero_residual_x_px": float(zero_residual[index, 0]),
            "zero_residual_y_px": float(zero_residual[index, 1]),
            "zero_residual_l2_px": float(np.linalg.norm(zero_residual[index])),
            "bounded_residual_x_px": float(bounded_residual[index, 0]),
            "bounded_residual_y_px": float(bounded_residual[index, 1]),
            "bounded_residual_l2_px": float(np.linalg.norm(bounded_residual[index])),
            "unbounded_residual_x_px": float(unbounded_residual[index, 0]),
            "unbounded_residual_y_px": float(unbounded_residual[index, 1]),
            "unbounded_residual_l2_px": float(np.linalg.norm(unbounded_residual[index])),
        })
    with (out_dir / "per_joint_residuals_v88.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"[PASS] V88_RESIDUAL_GEOMETRY_REPORT={out_dir / 'residual_geometry_report_v88.json'}")
    print(f"[PASS] V88_PER_JOINT_TABLE={out_dir / 'per_joint_residuals_v88.csv'}")
    print("[HOLD] V88_AUTHORIZES_OPTIMIZER=False")


if __name__ == "__main__":
    main()
