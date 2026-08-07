#!/usr/bin/env python3
"""Assemble and audit the read-only 42x22 translation+scale+articulation Jacobian."""
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


def select_matrix(arr: np.ndarray, cols: int, index: int, name: str) -> np.ndarray:
    if arr.shape == (42, cols):
        return arr
    if arr.ndim == 3 and arr.shape[1:] == (42, cols):
        if not 0 <= index < arr.shape[0]:
            raise ValueError(f"{name}: base index {index} outside shape {arr.shape}")
        return arr[index]
    raise ValueError(f"{name}: expected (42,{cols}) or (S,42,{cols}), got {arr.shape}")


def select_scale(arr: np.ndarray, index: int) -> np.ndarray:
    if arr.shape == (42,):
        return arr.reshape(42, 1)
    if arr.shape == (42, 1):
        return arr
    if arr.ndim == 3 and arr.shape[1:] == (42, 1):
        if not 0 <= index < arr.shape[0]:
            raise ValueError(f"scale: base index {index} outside shape {arr.shape}")
        return arr[index]
    raise ValueError(f"scale: expected (42,), (42,1), or (S,42,1), got {arr.shape}")


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


def retained_svd(A: np.ndarray, rel: float, absolute: float) -> dict[str, Any]:
    U, s, Vt = np.linalg.svd(A, full_matrices=False)
    threshold = max(absolute, rel * float(s[0]) if s.size else absolute)
    keep = s >= threshold
    retained = s[keep]
    condition = float(retained[0] / retained[-1]) if retained.size else math.inf
    return {
        "U": U[:, keep],
        "singular_values": s,
        "threshold": threshold,
        "rank": int(keep.sum()),
        "condition": condition,
        "retained_singular_values": retained,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--translation-jacobians", type=Path, required=True)
    p.add_argument("--scale-jacobian", type=Path, required=True)
    p.add_argument("--articulation-jacobians", type=Path, required=True)
    p.add_argument("--translation-policy", type=Path, required=True)
    p.add_argument("--capacity-policy", type=Path, required=True)
    p.add_argument("--weights", type=Path)
    p.add_argument("--identity-weights-confirmed", action="store_true")
    p.add_argument("--base-scale-index", type=int, default=1)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report_path = args.out_dir / "expanded_jacobian_closure_report_v99_8.json"

    paths = {
        "translation_jacobians": args.translation_jacobians,
        "scale_jacobian": args.scale_jacobian,
        "articulation_jacobians": args.articulation_jacobians,
        "translation_policy": args.translation_policy,
        "capacity_policy": args.capacity_policy,
    }
    if args.weights is not None:
        paths["weights"] = args.weights
    missing = [k for k, v in paths.items() if not v.is_file()]
    if missing:
        report_path.write_text(json.dumps({
            "schema": "expanded_jacobian_closure_report_v99_8",
            "decision": "hold_missing_inputs_v99_8",
            "missing": missing,
            "authorizes_optimizer": False,
        }, indent=2) + "\n")
        print(f"[HOLD] V99_8_MISSING={missing} REPORT={report_path}")
        return 0

    try:
        policy = load_json(args.capacity_policy)
        if policy.get("authorizes_capacity_execution") is not True:
            raise ValueError("capacity policy has not authorized the one read-only capacity execution")
        t_policy = load_json(args.translation_policy)
        radius = nested_number(t_policy, ("radius", "translation_l2_radius", "trust_radius"))
        if radius is None or radius <= 0:
            raise ValueError("cannot recover positive frozen translation radius")

        Jt = select_matrix(load_array(args.translation_jacobians), 3, args.base_scale_index, "translation")
        Js = select_scale(load_array(args.scale_jacobian), args.base_scale_index)
        Ja = select_matrix(load_array(args.articulation_jacobians), 18, args.base_scale_index, "articulation")
        for name, arr in (("Jt", Jt), ("Js", Js), ("Ja", Ja)):
            if not np.isfinite(arr).all():
                raise ValueError(f"{name} contains non-finite values")

        J_old = np.concatenate((Jt, Ja), axis=1)
        J = np.concatenate((Jt, Js, Ja), axis=1)
        if J.shape != (42, 22):
            raise ValueError(f"expanded Jacobian shape is {J.shape}, expected (42,22)")

        weights, weight_source = load_weights(args.weights, args.identity_weights_confirmed)
        sqrt_w = np.sqrt(weights)
        scale_bounds = policy["scale"]["physical_bounds"]
        log_lo, log_hi = math.log(float(scale_bounds[0])), math.log(float(scale_bounds[1]))
        scale_full_bound = max(abs(log_lo), abs(log_hi))
        art_bound = math.radians(float(policy.get("articulation_per_variable_degrees", 10.0)))
        bounds_old = np.array([radius] * 3 + [art_bound] * 18, dtype=np.float64)
        bounds_new = np.array([radius] * 3 + [scale_full_bound] + [art_bound] * 18, dtype=np.float64)

        A_old = sqrt_w[:, None] * (J_old * bounds_old[None, :])
        A_new = sqrt_w[:, None] * (J * bounds_new[None, :])
        rank_policy = policy.get("rank_policy", {})
        rel = float(rank_policy.get("relative_singular_cutoff", 1e-3))
        absolute = float(rank_policy.get("absolute_singular_cutoff_px_per_full_bound", 0.25))
        max_cond = float(rank_policy.get("maximum_effective_condition_number", 1e4))
        old = retained_svd(A_old, rel, absolute)
        new = retained_svd(A_new, rel, absolute)

        scale_vec = sqrt_w * Js[:, 0] * scale_full_bound
        if old["U"].shape[1]:
            scale_orth = scale_vec - old["U"] @ (old["U"].T @ scale_vec)
        else:
            scale_orth = scale_vec
        scale_norm = float(np.linalg.norm(scale_vec))
        scale_orth_norm = float(np.linalg.norm(scale_orth))
        scale_novelty_fraction = scale_orth_norm / max(scale_norm, 1e-30)

        np.save(args.out_dir / "expanded_jacobian_42x22_v99_8.npy", J)
        np.save(args.out_dir / "frozen_old_combined_jacobian_42x21_v99_8.npy", J_old)
        np.save(args.out_dir / "scale_orthogonal_residual_v99_8.npy", scale_orth)

        checks = {
            "shape_42x22": J.shape == (42, 22),
            "expanded_effective_rank_not_lower": new["rank"] >= old["rank"],
            "expanded_condition_within_policy": new["condition"] <= max_cond,
            "scale_column_nonzero": scale_norm > 0.0,
        }
        passed = all(checks.values())
        report = {
            "schema": "expanded_jacobian_closure_report_v99_8",
            "decision": "pass_expanded_jacobian_closure_v99_8" if passed else "hold_expanded_jacobian_closure_v99_8",
            "weighting_source": weight_source,
            "base_scale_index": args.base_scale_index,
            "constraints": {
                "translation_l2_radius": radius,
                "scale_log_bounds": [log_lo, log_hi],
                "scale_physical_bounds": scale_bounds,
                "articulation_bound_degrees": math.degrees(art_bound),
            },
            "old_combined": {
                "shape": list(J_old.shape),
                "effective_rank": old["rank"],
                "effective_condition_number": old["condition"],
                "singular_threshold": old["threshold"],
                "singular_values": old["singular_values"].tolist(),
            },
            "expanded": {
                "shape": list(J.shape),
                "effective_rank": new["rank"],
                "effective_condition_number": new["condition"],
                "singular_threshold": new["threshold"],
                "singular_values": new["singular_values"].tolist(),
            },
            "scale_novelty_diagnostic": {
                "bound_normalized_scale_column_norm": scale_norm,
                "orthogonal_residual_norm": scale_orth_norm,
                "novelty_fraction": scale_novelty_fraction,
                "note": "diagnostic only; bounded capacity remains the authorizing test",
            },
            "checks": checks,
            "failed_checks": [k for k, v in checks.items() if not v],
            "inputs": {k: {"path": str(v), "sha256": sha256(v)} for k, v in paths.items()},
            "outputs_are_read_only": True,
            "authorizes_optimizer": False,
        }
        report_path.write_text(json.dumps(report, indent=2) + "\n")
        print(f"[{'PASS' if passed else 'HOLD'}] V99_8_DECISION={report['decision']} REPORT={report_path}")
        return 0
    except Exception as error:
        report_path.write_text(json.dumps({
            "schema": "expanded_jacobian_closure_report_v99_8",
            "decision": "hold_expanded_jacobian_input_or_policy_v99_8",
            "error": f"{type(error).__name__}: {error}",
            "authorizes_optimizer": False,
        }, indent=2) + "\n")
        print(f"[HOLD] V99_8_ERROR={type(error).__name__}: {error} REPORT={report_path}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
