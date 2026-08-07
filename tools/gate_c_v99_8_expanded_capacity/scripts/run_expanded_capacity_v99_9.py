#!/usr/bin/env python3
"""CPU-only bounded capacity analysis for translation+scale+articulation.

Solves the linearized convex problem

  min ||sqrt(W) (r - J x)||^2

under one translation L2 ball, one asymmetric log-scale interval, and
18 independent articulation boxes. It never runs MANO or writes a mesh.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def load_array(path: Path) -> np.ndarray:
    return np.asarray(np.load(path, allow_pickle=False), dtype=np.float64)


def flat42(arr: np.ndarray, name: str) -> np.ndarray:
    if arr.size != 42:
        raise ValueError(f"{name} must contain 42 values, got {arr.shape}")
    return arr.reshape(42)


def nested_number(data: Any, keys: tuple[str, ...]) -> float | None:
    if isinstance(data, dict):
        for k in keys:
            if isinstance(data.get(k), (int, float)):
                return float(data[k])
        for value in data.values():
            result = nested_number(value, keys)
            if result is not None:
                return result
    elif isinstance(data, list):
        for value in data:
            result = nested_number(value, keys)
            if result is not None:
                return result
    return None


def load_weights(path: Path | None, identity: bool) -> tuple[np.ndarray, str]:
    if path is not None:
        w = load_array(path).reshape(-1)
        if w.size == 21:
            w = np.repeat(w, 2)
        if w.size != 42 or not np.isfinite(w).all() or np.any(w < 0) or w.sum() <= 0:
            raise ValueError("weights must be 21 or 42 finite non-negative values with positive sum")
        return w, f"file:{path}"
    if identity:
        return np.ones(42, dtype=np.float64), "identity_weighting_explicitly_confirmed"
    raise ValueError("supply --weights or source-proven --identity-weights-confirmed")


def projection(x: np.ndarray, radius: float, scale_lo: float, scale_hi: float, art_bound: float) -> np.ndarray:
    y = np.asarray(x, dtype=np.float64).copy()
    norm = float(np.linalg.norm(y[:3]))
    if norm > radius and norm > 0:
        y[:3] *= radius / norm
    y[3] = np.clip(y[3], scale_lo, scale_hi)
    y[4:] = np.clip(y[4:], -art_bound, art_bound)
    return y


def objective(A: np.ndarray, b: np.ndarray, x: np.ndarray) -> float:
    d = A @ x - b
    return 0.5 * float(d @ d)


def fista(A: np.ndarray, b: np.ndarray, radius: float, scale_lo: float, scale_hi: float, art_bound: float, max_iter: int, tol: float):
    spectral = float(np.linalg.norm(A, ord=2))
    L = max(spectral * spectral, 1e-12)
    x = np.zeros(A.shape[1], dtype=np.float64)
    y = x.copy()
    theta = 1.0
    prev = objective(A, b, x)
    converged = False
    iters = 0
    for i in range(1, max_iter + 1):
        grad = A.T @ (A @ y - b)
        x_new = projection(y - grad / L, radius, scale_lo, scale_hi, art_bound)
        obj = objective(A, b, x_new)
        if obj > prev + 1e-14:
            y = x.copy(); theta = 1.0
            grad = A.T @ (A @ y - b)
            x_new = projection(y - grad / L, radius, scale_lo, scale_hi, art_bound)
            obj = objective(A, b, x_new)
        old = x
        step = float(np.linalg.norm(x_new - x))
        x = x_new; prev = obj; iters = i
        if step <= tol * max(1.0, float(np.linalg.norm(old))):
            converged = True
            break
        theta_new = 0.5 * (1 + math.sqrt(1 + 4 * theta * theta))
        candidate = x + ((theta - 1) / theta_new) * (x - old)
        if float(np.dot(candidate - x, x - old)) > 0:
            y = x.copy(); theta = 1.0
        else:
            y = candidate; theta = theta_new
    grad = A.T @ (A @ x - b)
    pg = float(np.linalg.norm(x - projection(x - grad / L, radius, scale_lo, scale_hi, art_bound)))
    return x, {"solver": "projected_fista_mixed_constraints", "converged": converged, "iterations": iters, "objective": objective(A, b, x), "projected_gradient_mapping_norm": pg, "lipschitz": L}


def scipy_check(A, b, radius, scale_lo, scale_hi, art_bound, initial):
    try:
        from scipy.optimize import minimize
    except Exception as error:
        return None, {"available": False, "success": False, "error": f"{type(error).__name__}: {error}"}
    def fun(x): return objective(A, b, x)
    def jac(x): return A.T @ (A @ x - b)
    constraint = ({
        "type": "ineq",
        "fun": lambda x: radius * radius - float(x[:3] @ x[:3]),
        "jac": lambda x: np.concatenate((-2 * x[:3], np.zeros(19))),
    },)
    bounds = [(-radius, radius)] * 3 + [(scale_lo, scale_hi)] + [(-art_bound, art_bound)] * 18
    result = minimize(fun, initial, jac=jac, method="SLSQP", bounds=bounds, constraints=constraint, options={"maxiter": 10000, "ftol": 1e-12, "disp": False})
    x = np.asarray(result.x, dtype=np.float64)
    return x, {"available": True, "success": bool(result.success), "status": int(result.status), "message": str(result.message), "iterations": int(getattr(result, "nit", -1)), "objective": fun(x)}


def metrics(residual: np.ndarray, weights: np.ndarray, norm: float) -> dict[str, float]:
    pts = residual.reshape(21, 2)
    d = np.linalg.norm(pts, axis=1)
    energy = float(np.sum(weights * residual * residual))
    kp_rmse = float(np.sqrt(np.mean(d * d)))
    p95 = float(np.percentile(d, 95))
    return {
        "weighted_coordinate_energy": energy,
        "weighted_coordinate_norm": math.sqrt(max(energy, 0.0)),
        "coordinate_rmse_px": float(np.sqrt(np.mean(residual * residual))),
        "keypoint_euclidean_rmse_px": kp_rmse,
        "keypoint_euclidean_p95_px": p95,
        "normalized_keypoint_rmse": kp_rmse / norm,
        "normalized_keypoint_p95": p95 / norm,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--expanded-jacobian", type=Path, required=True)
    p.add_argument("--zero", type=Path, required=True)
    p.add_argument("--target", type=Path, required=True)
    p.add_argument("--residual", type=Path, required=True)
    p.add_argument("--normalization", type=Path, required=True)
    p.add_argument("--translation-policy", type=Path, required=True)
    p.add_argument("--capacity-policy", type=Path, required=True)
    p.add_argument("--weights", type=Path)
    p.add_argument("--identity-weights-confirmed", action="store_true")
    p.add_argument("--source-precision-bound-px", type=float, default=0.05)
    p.add_argument("--max-iter", type=int, default=300000)
    p.add_argument("--tolerance", type=float, default=1e-11)
    p.add_argument("--require-scipy-crosscheck", action="store_true")
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.out_dir / "expanded_bounded_capacity_report_v99_9.json"
    route_path = args.out_dir / "expanded_bounded_capacity_route_v99_9.json"
    paths = {"expanded_jacobian": args.expanded_jacobian, "zero": args.zero, "target": args.target, "residual": args.residual, "normalization": args.normalization, "translation_policy": args.translation_policy, "capacity_policy": args.capacity_policy}
    if args.weights is not None: paths["weights"] = args.weights
    missing = [k for k, v in paths.items() if not v.is_file()]
    if missing:
        report_path.write_text(json.dumps({"schema": "expanded_bounded_capacity_report_v99_9", "decision": "hold_missing_inputs_v99_9", "missing": missing, "authorizes_optimizer": False}, indent=2) + "\n")
        print(f"[HOLD] V99_9_MISSING={missing} REPORT={report_path}")
        return 0
    try:
        policy = load_json(args.capacity_policy)
        if policy.get("authorizes_capacity_execution") is not True:
            raise ValueError("capacity execution is not authorized by v99.8 policy")
        J = load_array(args.expanded_jacobian)
        if J.shape != (42, 22) or not np.isfinite(J).all():
            raise ValueError(f"expanded Jacobian must be finite (42,22), got {J.shape}")
        zero = flat42(load_array(args.zero), "zero")
        target = flat42(load_array(args.target), "target")
        residual = flat42(load_array(args.residual), "residual")
        identity_error = target - zero - residual
        identity_max = float(np.max(np.abs(identity_error)))
        if identity_max > args.source_precision_bound_px:
            raise ValueError(f"target-zero does not reproduce residual: max={identity_max}")
        n_arr = load_array(args.normalization).reshape(-1)
        if n_arr.size != 1 or not np.isfinite(n_arr[0]) or n_arr[0] <= 0:
            raise ValueError("normalization must be one positive finite scalar")
        normalization = float(n_arr[0])
        t_policy = load_json(args.translation_policy)
        radius = nested_number(t_policy, ("radius", "translation_l2_radius", "trust_radius"))
        if radius is None or radius <= 0:
            raise ValueError("cannot recover positive frozen translation radius")
        physical_bounds = policy["scale"]["physical_bounds"]
        scale_lo, scale_hi = math.log(float(physical_bounds[0])), math.log(float(physical_bounds[1]))
        art_deg = float(policy.get("articulation_per_variable_degrees", 10.0))
        art_bound = math.radians(abs(art_deg))
        acceptance = policy.get("acceptance", {})
        required = ["minimum_weighted_residual_energy_coverage", "maximum_bounded_residual_norm_ratio", "minimum_predicted_rmse_reduction_fraction", "maximum_predicted_normalized_rmse", "maximum_predicted_normalized_p95", "maximum_translation_bound_fraction", "maximum_scale_bound_fraction", "maximum_single_articulation_bound_fraction", "maximum_saturated_articulation_fraction", "maximum_solver_prediction_difference_px_l2"]
        absent = [k for k in required if k not in acceptance]
        if absent: raise ValueError(f"capacity policy missing acceptance fields: {absent}")
        weights, weight_source = load_weights(args.weights, args.identity_weights_confirmed)
        sqrt_w = np.sqrt(weights)
        A = sqrt_w[:, None] * J
        b = sqrt_w * residual
        x1, info1 = fista(A, b, radius, scale_lo, scale_hi, art_bound, args.max_iter, args.tolerance)
        x2, info2 = scipy_check(A, b, radius, scale_lo, scale_hi, art_bound, x1)
        if args.require_scipy_crosscheck and not info2.get("success", False):
            raise ValueError(f"required SciPy cross-check failed: {info2}")
        if x2 is not None and info2.get("success", False):
            o1, o2 = objective(A, b, x1), objective(A, b, x2)
            obj_diff = abs(o1 - o2) / max(1.0, abs(o1), abs(o2))
            pred_diff = float(np.linalg.norm(J @ (x1 - x2)))
        else:
            obj_diff = None; pred_diff = None
        change = J @ x1
        remaining = residual - change
        before, after = metrics(residual, weights, normalization), metrics(remaining, weights, normalization)
        energy_coverage = 1 - after["weighted_coordinate_energy"] / max(before["weighted_coordinate_energy"], 1e-30)
        norm_ratio = after["weighted_coordinate_norm"] / max(before["weighted_coordinate_norm"], 1e-30)
        rmse_reduction = 1 - after["keypoint_euclidean_rmse_px"] / max(before["keypoint_euclidean_rmse_px"], 1e-30)
        t = x1[:3]; log_scale = float(x1[3]); a = x1[4:]
        t_frac = float(np.linalg.norm(t)) / radius
        scale_frac = log_scale / scale_hi if log_scale >= 0 else abs(log_scale) / abs(scale_lo)
        physical_scale = math.exp(log_scale)
        a_frac = np.abs(a) / art_bound
        sat_threshold = float(policy.get("saturation_threshold_fraction", 0.95))
        sat_count = int(np.sum(a_frac >= sat_threshold)); sat_fraction = sat_count / 18
        checks = {
            "primary_solver_converged": bool(info1["converged"]),
            "required_crosscheck_succeeded": bool(info2.get("success", False)) if args.require_scipy_crosscheck else True,
            "solver_objectives_agree": obj_diff is None or obj_diff <= 1e-6,
            "maximum_solver_prediction_difference_px_l2": pred_diff is None or pred_diff <= float(acceptance["maximum_solver_prediction_difference_px_l2"]),
            "minimum_weighted_residual_energy_coverage": energy_coverage >= float(acceptance["minimum_weighted_residual_energy_coverage"]),
            "maximum_bounded_residual_norm_ratio": norm_ratio <= float(acceptance["maximum_bounded_residual_norm_ratio"]),
            "minimum_predicted_rmse_reduction_fraction": rmse_reduction >= float(acceptance["minimum_predicted_rmse_reduction_fraction"]),
            "maximum_predicted_normalized_rmse": after["normalized_keypoint_rmse"] <= float(acceptance["maximum_predicted_normalized_rmse"]),
            "maximum_predicted_normalized_p95": after["normalized_keypoint_p95"] <= float(acceptance["maximum_predicted_normalized_p95"]),
            "maximum_translation_bound_fraction": t_frac <= float(acceptance["maximum_translation_bound_fraction"]),
            "maximum_scale_bound_fraction": scale_frac <= float(acceptance["maximum_scale_bound_fraction"]),
            "maximum_single_articulation_bound_fraction": float(np.max(a_frac)) <= float(acceptance["maximum_single_articulation_bound_fraction"]),
            "maximum_saturated_articulation_fraction": sat_fraction <= float(acceptance["maximum_saturated_articulation_fraction"]),
        }
        passed = all(checks.values())
        np.save(args.out_dir / "diagnostic_translation_v99_9.npy", t)
        np.save(args.out_dir / "diagnostic_log_hand_scale_v99_9.npy", np.array([log_scale]))
        np.save(args.out_dir / "diagnostic_articulation_v99_9.npy", a)
        np.save(args.out_dir / "predicted_keypoints_v99_9.npy", (zero + change).reshape(21, 2))
        np.save(args.out_dir / "remaining_residual_v99_9.npy", remaining.reshape(21, 2))
        report = {
            "schema": "expanded_bounded_capacity_report_v99_9",
            "decision": "pass_expanded_bounded_capacity_v99_9" if passed else "reject_expanded_bounded_capacity_v99_9",
            "scope": "read_only_linearized_capacity_no_mano_no_mesh_no_optimizer",
            "weighting_source": weight_source,
            "input_identity": {"target_zero_residual_max_error_px": identity_max, "source_precision_bound_px": args.source_precision_bound_px},
            "constraints": {"translation_l2_radius": radius, "scale_log_bounds": [scale_lo, scale_hi], "scale_physical_bounds": physical_bounds, "articulation_bound_degrees": art_deg, "initialization": "all_zero"},
            "solver": {"primary": info1, "crosscheck": info2, "objective_relative_difference": obj_diff, "prediction_difference_px_l2": pred_diff},
            "metrics": {
                "before": before, "after": after,
                "weighted_residual_energy_coverage": energy_coverage,
                "bounded_residual_norm_ratio": norm_ratio,
                "predicted_rmse_reduction_fraction": rmse_reduction,
                "translation": t.tolist(), "translation_norm": float(np.linalg.norm(t)), "translation_bound_fraction": t_frac,
                "global_log_hand_scale": log_scale, "physical_hand_scale": physical_scale, "scale_bound_fraction": scale_frac,
                "articulation_radians": a.tolist(), "articulation_degrees": np.degrees(a).tolist(), "articulation_bound_fractions": a_frac.tolist(),
                "maximum_articulation_bound_fraction": float(np.max(a_frac)), "saturation_threshold_fraction": sat_threshold, "saturated_articulation_count": sat_count, "saturated_articulation_fraction": sat_fraction,
            },
            "acceptance": acceptance,
            "checks": checks,
            "failed_checks": [k for k, v in checks.items() if not v],
            "inputs": {k: {"path": str(v), "sha256": sha256(v)} for k, v in paths.items()},
            "outputs_are_diagnostic_only": True,
            "authorizes_optimizer": False,
            "authorizes_nonzero_mesh": False,
        }
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        route = {"schema": "expanded_bounded_capacity_route_v99_9", "decision": "prepare_v99_10_non_authorizing_capacity_review" if passed else "prepare_v99_10_rejection_or_candidate_audit", "capacity_passed": passed, "authorizes_optimizer": False, "authorizes_nonzero_mesh": False}
        route_path.write_text(json.dumps(route, indent=2) + "\n")
        print(f"[{'PASS' if passed else 'HOLD'}] V99_9_DECISION={report['decision']} REPORT={report_path} ROUTE={route_path}")
        return 0
    except Exception as error:
        report_path.write_text(json.dumps({"schema": "expanded_bounded_capacity_report_v99_9", "decision": "hold_expanded_capacity_input_or_solver_v99_9", "error": f"{type(error).__name__}: {error}", "authorizes_optimizer": False}, indent=2) + "\n")
        print(f"[HOLD] V99_9_ERROR={type(error).__name__}: {error} REPORT={report_path}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
