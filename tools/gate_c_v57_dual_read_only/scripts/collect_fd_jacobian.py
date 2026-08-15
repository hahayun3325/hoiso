from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np

from common import (
    ProbeConfigError, as_path, cosine, ensure_keypoint_pair, load_adapter,
    read_json, read_keypoints, read_manifest, write_csv, write_json,
)


def token(x: float) -> str:
    return (f"{x:g}").replace(".", "p")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--preflight", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)
    (out / "samples").mkdir(parents=True, exist_ok=True)

    try:
        cfg = read_json(args.config)
        pre = read_json(args.preflight)
        if pre.get("status") != "PASS":
            write_json(out / "fd_collection.json", {
                "status": "HOLD_PREFLIGHT_NOT_PASS",
                "preflight_status": pre.get("status"),
            })
            print("[HOLD] preflight did not pass; no perturbations evaluated")
            return 0
        thresholds = read_json(as_path(cfg, "thresholds"))
        rows = [r for r in read_manifest(as_path(cfg, "parameter_manifest")) if r["enabled"]]
        adapter = load_adapter(as_path(cfg, "adapter"))
        context = adapter.load_context(cfg.get("adapter_context", {}))
        expected_zero = read_keypoints(as_path(cfg, "expected_zero_keypoints"))
        zero_before = np.asarray(adapter.project_keypoints(context, {}), dtype=np.float64)[:, :2]
        ensure_keypoint_pair(zero_before, expected_zero, "zero_before")

        multipliers = [float(x) for x in cfg.get("fd_step_multipliers", [0.5, 1.0, 2.0])]
        base_multiplier = float(cfg.get("base_step_multiplier", 1.0))
        if base_multiplier not in multipliers:
            raise ProbeConfigError("base_step_multiplier must be in fd_step_multipliers")
        jacobians: dict[float, np.ndarray] = {}
        derivative_by_multiplier: dict[float, list[np.ndarray]] = {m: [] for m in multipliers}

        for row in rows:
            name = row["name"]
            for m in multipliers:
                h = row["step"] * m
                plus = np.asarray(adapter.project_keypoints(context, {name: +h}), dtype=np.float64)[:, :2]
                minus = np.asarray(adapter.project_keypoints(context, {name: -h}), dtype=np.float64)[:, :2]
                ensure_keypoint_pair(plus, zero_before, f"{name} plus")
                ensure_keypoint_pair(minus, zero_before, f"{name} minus")
                np.save(out / "samples" / f"{name}__plus__m{token(m)}.npy", plus)
                np.save(out / "samples" / f"{name}__minus__m{token(m)}.npy", minus)
                derivative_by_multiplier[m].append(((plus - minus) / (2.0 * h)).reshape(-1))

        for m in multipliers:
            J = np.stack(derivative_by_multiplier[m], axis=1)
            jacobians[m] = J
            np.save(out / f"jacobian__m{token(m)}.npy", J)

        base = jacobians[base_multiplier]
        sthr = thresholds["fd_stability"]
        near_zero = float(sthr["near_zero_column_norm"])
        stability_rows = []
        unstable = 0
        assessable = 0
        for j, row in enumerate(rows):
            ref = base[:, j]
            ref_norm = float(np.linalg.norm(ref))
            item = {
                "name": row["name"],
                "group": row["group"],
                "base_derivative_norm": ref_norm,
                "near_zero": ref_norm <= near_zero,
            }
            stable = True
            if ref_norm > near_zero:
                assessable += 1
                for m in multipliers:
                    if m == base_multiplier:
                        continue
                    col = jacobians[m][:, j]
                    n = float(np.linalg.norm(col))
                    c = cosine(ref, col)
                    ratio = n / ref_norm if ref_norm > 0 else float("nan")
                    item[f"cosine_m{token(m)}"] = c
                    item[f"norm_ratio_m{token(m)}"] = ratio
                    stable = stable and c >= float(sthr["min_column_cosine"]) and float(sthr["norm_ratio_min"]) <= ratio <= float(sthr["norm_ratio_max"])
            item["stable"] = bool(stable)
            if not stable:
                unstable += 1
            stability_rows.append(item)

        zero_after = np.asarray(adapter.project_keypoints(context, {}), dtype=np.float64)[:, :2]
        ensure_keypoint_pair(zero_after, zero_before, "zero mutation check")
        mutation = np.linalg.norm(zero_after - zero_before, axis=1)
        unstable_fraction = unstable / max(assessable, 1)
        global_pass = unstable_fraction <= float(sthr["max_unstable_fraction"]) and float(np.max(mutation)) <= float(thresholds["zero_identity"]["max_px"])

        write_csv(
            out / "fd_stability.csv", stability_rows,
            fieldnames=list(stability_rows[0].keys()),
        )
        write_json(out / "fd_collection.json", {
            "status": "PASS" if global_pass else "HOLD_NUMERICAL_INSTABILITY",
            "global_pass": bool(global_pass),
            "parameter_count": len(rows),
            "assessable_parameter_count": assessable,
            "unstable_parameter_count": unstable,
            "unstable_fraction": unstable_fraction,
            "zero_state_mutation_max_px": float(np.max(mutation)),
            "base_step_multiplier": base_multiplier,
            "multipliers": multipliers,
            "parameter_names": [r["name"] for r in rows],
            "parameter_groups": [r["group"] for r in rows],
            "bounds": [r["bound"] for r in rows],
        })
        print("[PASS] finite-difference collection" if global_pass else "[HOLD] finite-difference instability")
        return 0
    except ProbeConfigError as exc:
        write_json(out / "fd_collection.json", {"status": "CONFIG_ERROR", "message": str(exc)})
        print(f"[CONFIG_ERROR] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        write_json(out / "fd_collection.json", {"status": "ADAPTER_ERROR", "message": repr(exc)})
        print(f"[ADAPTER_ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
