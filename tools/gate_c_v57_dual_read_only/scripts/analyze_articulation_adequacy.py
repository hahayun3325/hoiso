from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import lsq_linear, minimize

from common import (
    ProbeConfigError, as_path, keypoint_metrics, read_json, read_manifest,
    write_csv, write_json,
)


def token(x: float) -> str:
    return (f"{x:g}").replace(".", "p")


def weighted_norm(v: np.ndarray, wcoord: np.ndarray) -> float:
    return float(np.linalg.norm(wcoord * v))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--preflight-dir", required=True)
    ap.add_argument("--fd-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    pre_dir = Path(args.preflight_dir)
    fd_dir = Path(args.fd_dir)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    try:
        cfg = read_json(args.config)
        thresholds = read_json(as_path(cfg, "thresholds"))
        pre = read_json(pre_dir / "preflight.json")
        fd = read_json(fd_dir / "fd_collection.json")
        if pre.get("status") != "PASS" or fd.get("status") != "PASS":
            write_json(out / "analysis_summary.json", {
                "status": "HOLD_UPSTREAM_NOT_PASS",
                "preflight_status": pre.get("status"),
                "fd_status": fd.get("status"),
            })
            print("[HOLD] preflight or finite-difference collection did not pass")
            return 0

        zero = np.load(pre_dir / "zero_projection.npy").astype(np.float64)
        target = np.load(pre_dir / "target_keypoints.npy").astype(np.float64)
        confidence = np.load(pre_dir / "confidence.npy").astype(np.float64).reshape(-1)
        rows_all = read_manifest(as_path(cfg, "parameter_manifest"))
        rows = [r for r in rows_all if r["enabled"]]
        base_m = float(fd["base_step_multiplier"])
        J = np.load(fd_dir / f"jacobian__m{token(base_m)}.npy").astype(np.float64)
        if J.shape != (zero.size, len(rows)):
            raise ProbeConfigError(f"Jacobian shape {J.shape} incompatible with {zero.shape} and {len(rows)} params")

        # Parse stability without pandas.
        import csv
        stability = {}
        with (fd_dir / "fd_stability.csv").open("r", encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                stability[r["name"]] = str(r.get("stable", "")).lower() == "true"
        stable_mask = np.array([stability.get(r["name"], False) for r in rows], dtype=bool)

        conf = np.clip(confidence, 0.0, 1.0)
        wcoord = np.repeat(np.sqrt(conf), 2)
        residual = (target - zero).reshape(-1)
        b = wcoord * residual
        norm_scale = float(cfg["normalization_scale_px"])
        if not np.isfinite(norm_scale) or norm_scale <= 0:
            raise ProbeConfigError("normalization_scale_px must be the frozen positive Branch-E denominator")

        before_metrics = keypoint_metrics(zero, target, conf)
        before_metrics["normalized_rmse"] = before_metrics["rmse_px"] / norm_scale
        before_metrics["normalized_p95"] = before_metrics["p95_px"] / norm_scale

        name_to_index = {r["name"]: i for i, r in enumerate(rows)}
        group_to_indices: dict[str, list[int]] = {}
        for i, r in enumerate(rows):
            group_to_indices.setdefault(r["group"], []).append(i)

        block_results = {}
        summary_rows = []
        svd_cfg = thresholds["svd"]
        adeq = thresholds["adequacy"]

        for block_name, groups in cfg.get("analysis_blocks", {}).items():
            idx = sorted({i for g in groups for i in group_to_indices.get(g, [])})
            idx = [i for i in idx if stable_mask[i]]
            if not idx:
                block_results[block_name] = {"status": "NOT_AVAILABLE", "groups": groups, "parameter_count": 0}
                continue
            bounds = np.array([rows[i]["bound"] for i in idx], dtype=np.float64)
            J_unweighted_bound = J[:, idx] * bounds[None, :]
            A = wcoord[:, None] * J_unweighted_bound
            U, s, Vt = np.linalg.svd(A, full_matrices=False)
            if s.size == 0 or s[0] <= 0:
                rank = 0
                cutoff = float("inf")
            else:
                cutoff = max(float(svd_cfg["relative_cutoff"]) * float(s[0]), float(svd_cfg["absolute_px_per_bound"]))
                rank = int(np.sum(s >= cutoff))
            if rank > 0:
                Ur = U[:, :rank]
                projected = Ur @ (Ur.T @ b)
                unbounded_after = b - projected
                condition = float(s[0] / s[rank - 1])
            else:
                projected = np.zeros_like(b)
                unbounded_after = b.copy()
                condition = float("inf")

            box_sol = lsq_linear(A, b, bounds=(-1.0, 1.0), method="trf", lsmr_tol="auto", verbose=0)
            x0 = np.asarray(box_sol.x, dtype=np.float64)

            # Enforce source-registered group L2 trust regions, especially the
            # Branch-E translation radius. The box bounds alone would permit a
            # sqrt(3)-larger 3D translation when all axes saturate.
            group_limits_cfg = cfg.get("group_l2_limits", {}) or {}
            constraints = []
            group_local: dict[str, list[int]] = {}
            for local_j, global_i in enumerate(idx):
                group_local.setdefault(rows[global_i]["group"], []).append(local_j)
            resolved_group_limits: dict[str, float] = {}
            for group, locs in group_local.items():
                if group not in group_limits_cfg:
                    continue
                try:
                    limit = float(group_limits_cfg[group])
                except Exception as exc:
                    raise ProbeConfigError(f"Invalid group_l2_limits[{group!r}]: {exc}") from exc
                if not np.isfinite(limit) or limit <= 0:
                    raise ProbeConfigError(f"group_l2_limits[{group!r}] must be a positive source-registered value")
                resolved_group_limits[group] = limit
                locs_arr = np.asarray(locs, dtype=int)
                bnd = bounds[locs_arr].copy()
                # Make the initial point feasible for SLSQP.
                norm0 = float(np.linalg.norm(bnd * x0[locs_arr]))
                if norm0 > limit and norm0 > 0:
                    x0[locs_arr] *= (0.999 * limit / norm0)
                constraints.append({
                    "type": "ineq",
                    "fun": (lambda x, li=locs_arr, bb=bnd, lim=limit: lim * lim - float(np.sum((bb * x[li]) ** 2))),
                    "jac": (lambda x, li=locs_arr, bb=bnd: np.bincount(li, weights=-2.0 * (bb ** 2) * x[li], minlength=x.size).astype(float)),
                })

            def objective(x):
                d = A @ x - b
                return 0.5 * float(d @ d)

            def objective_jac(x):
                return A.T @ (A @ x - b)

            if constraints:
                opt = minimize(
                    objective, x0, jac=objective_jac, method="SLSQP",
                    bounds=[(-1.0, 1.0)] * len(x0), constraints=constraints,
                    options={"maxiter": 500, "ftol": 1e-12, "disp": False},
                )
                x = np.asarray(opt.x, dtype=np.float64)
                optimizer_success = bool(opt.success)
                optimizer_message = str(opt.message)
            else:
                x = x0
                optimizer_success = bool(box_sol.success)
                optimizer_message = str(box_sol.message)

            group_norm_fractions = {}
            for group, limit in resolved_group_limits.items():
                locs = np.asarray(group_local[group], dtype=int)
                group_norm_fractions[group] = float(np.linalg.norm(bounds[locs] * x[locs]) / limit)
            max_group_norm_fraction = max(group_norm_fractions.values(), default=0.0)

            pred_delta = J_unweighted_bound @ x
            predicted = zero + pred_delta.reshape(zero.shape)
            after_metrics = keypoint_metrics(predicted, target, conf)
            after_metrics["normalized_rmse"] = after_metrics["rmse_px"] / norm_scale
            after_metrics["normalized_p95"] = after_metrics["p95_px"] / norm_scale
            after_w = b - A @ x
            bnorm = float(np.linalg.norm(b))
            after_norm = float(np.linalg.norm(after_w))
            coverage = 1.0 - (after_norm * after_norm / (bnorm * bnorm)) if bnorm > 0 else 1.0
            residual_ratio = after_norm / bnorm if bnorm > 0 else 0.0
            rmse_reduction = 1.0 - after_metrics["rmse_px"] / before_metrics["rmse_px"] if before_metrics["rmse_px"] > 0 else 0.0
            max_abs_x = float(np.max(np.abs(x))) if x.size else 0.0
            saturated_fraction = float(np.mean(np.abs(x) >= 0.95)) if x.size else 0.0
            condition_pass = rank > 0 and condition <= float(svd_cfg["max_effective_condition"])
            passes = (
                coverage >= float(adeq["min_bounded_energy_coverage"])
                and residual_ratio <= float(adeq["max_bounded_residual_ratio"])
                and rmse_reduction >= float(adeq["min_rmse_reduction_fraction"])
                and after_metrics["normalized_rmse"] <= float(adeq["max_predicted_normalized_rmse"])
                and after_metrics["normalized_p95"] <= float(adeq["max_predicted_normalized_p95"])
                and max_abs_x <= float(adeq["max_abs_bound_fraction"])
                and saturated_fraction <= float(adeq["max_saturated_fraction"])
                and max_group_norm_fraction <= float(adeq.get("max_group_norm_fraction", 1.0))
                and condition_pass
                and optimizer_success
            )
            params = []
            for local_j, global_i in enumerate(idx):
                params.append({
                    "name": rows[global_i]["name"],
                    "group": rows[global_i]["group"],
                    "bound": float(bounds[local_j]),
                    "bound_fraction": float(x[local_j]),
                    "predicted_delta": float(x[local_j] * bounds[local_j]),
                })
            np.save(out / f"predicted_keypoints__{block_name}.npy", predicted)
            write_csv(
                out / f"solution__{block_name}.csv", params,
                ["name", "group", "bound", "bound_fraction", "predicted_delta"],
            )
            result = {
                "status": "ADEQUATE" if passes else "INADEQUATE",
                "passes_adequacy": bool(passes),
                "groups": groups,
                "parameter_count": len(idx),
                "effective_rank": rank,
                "singular_values": [float(v) for v in s],
                "singular_cutoff": cutoff,
                "effective_condition": condition,
                "condition_pass": bool(condition_pass),
                "unbounded_weighted_residual_ratio": float(np.linalg.norm(unbounded_after) / bnorm) if bnorm > 0 else 0.0,
                "bounded_energy_coverage": coverage,
                "bounded_residual_ratio": residual_ratio,
                "rmse_reduction_fraction": rmse_reduction,
                "max_abs_bound_fraction": max_abs_x,
                "saturated_fraction": saturated_fraction,
                "optimizer_success": optimizer_success,
                "optimizer_message": optimizer_message,
                "group_norm_fractions": group_norm_fractions,
                "max_group_norm_fraction": max_group_norm_fraction,
                "before": before_metrics,
                "predicted_after": after_metrics,
                "parameters": params,
            }
            block_results[block_name] = result
            summary_rows.append({
                "block": block_name,
                "status": result["status"],
                "parameter_count": len(idx),
                "effective_rank": rank,
                "effective_condition": condition,
                "coverage": coverage,
                "residual_ratio": residual_ratio,
                "rmse_reduction": rmse_reduction,
                "predicted_nrmse": after_metrics["normalized_rmse"],
                "predicted_np95": after_metrics["normalized_p95"],
                "max_abs_bound_fraction": max_abs_x,
                "saturated_fraction": saturated_fraction,
                "max_group_norm_fraction": max_group_norm_fraction,
            })

        write_csv(
            out / "block_summary.csv", summary_rows,
            ["block", "status", "parameter_count", "effective_rank", "effective_condition", "coverage", "residual_ratio", "rmse_reduction", "predicted_nrmse", "predicted_np95", "max_abs_bound_fraction", "saturated_fraction", "max_group_norm_fraction"],
        )
        write_json(out / "analysis_summary.json", {
            "status": "COMPLETE",
            "normalization_scale_px": norm_scale,
            "before": before_metrics,
            "stable_parameter_count": int(np.sum(stable_mask)),
            "enabled_parameter_count": len(rows),
            "blocks": block_results,
            "authorizing_blocks": cfg.get("authorizing_blocks", []),
            "known_branch_e_translation_rejected": bool(cfg.get("known_branch_e_translation_rejected", False)),
        })
        print("[COMPLETE] read-only articulation span analysis")
        return 0
    except ProbeConfigError as exc:
        write_json(out / "analysis_summary.json", {"status": "CONFIG_ERROR", "message": str(exc)})
        print(f"[CONFIG_ERROR] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        write_json(out / "analysis_summary.json", {"status": "ANALYSIS_ERROR", "message": repr(exc)})
        print(f"[ANALYSIS_ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
