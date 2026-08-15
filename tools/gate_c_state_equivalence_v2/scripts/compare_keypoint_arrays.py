#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Tuple

from common import (
    load_array,
    load_thresholds,
    passes_identity,
    point_metrics,
    reflection_x,
    sha256_file,
    shape_metrics,
    write_json,
)


def parser() -> Tuple[argparse.Namespace, list[str]]:
    p = argparse.ArgumentParser(
        description=(
            "Compare two immutable keypoint arrays and apply a pre-registered "
            "identity tolerance. Reflection is diagnostic only."
        )
    )
    p.add_argument("--a", default="")
    p.add_argument("--b", default="")
    p.add_argument("--key-a", default="")
    p.add_argument("--key-b", default="")
    p.add_argument("--candidate-a", default="0")
    p.add_argument("--candidate-b", default="0")
    p.add_argument("--stage", default="unspecified_identity_stage")
    p.add_argument("--units", default="unspecified")
    p.add_argument("--thresholds", default="")
    p.add_argument("--max-abs", type=float, default=None)
    p.add_argument("--rmse", type=float, default=None)
    p.add_argument("--out", default="")
    return p.parse_known_args()


def infer_thresholds(stage: str, supplied: Dict[str, float], units: str) -> tuple[float, float, str]:
    name = stage.strip().lower()
    if name.startswith("h0"):
        return supplied["h0_max_abs_m"], supplied["h0_rmse_m"], "H0"
    if name.startswith("h1"):
        return supplied["h1_max_abs_m"], supplied["h1_rmse_m"], "H1"
    if name.startswith("h2"):
        return supplied["h2_max_abs_px"], supplied["h2_rmse_px"], "H2"
    if name.startswith("h3"):
        return supplied["h3_max_abs_m"], supplied["h3_rmse_m"], "H3"
    if name.startswith("h4"):
        return supplied["h4_max_abs_m"], supplied["h4_rmse_m"], "H4"
    if units.lower() in {"px", "pixel", "pixels"}:
        return supplied["h2_max_abs_px"], supplied["h2_rmse_px"], "CUSTOM_PIXEL"
    return supplied["h4_max_abs_m"], supplied["h4_rmse_m"], "CUSTOM_METRIC"


def main() -> int:
    args, unknown = parser()
    if unknown:
        print(f"[HOLD] Unknown arguments: {unknown}", file=sys.stderr)
        return 1
    if not args.a or not args.b:
        print("[HOLD] --a and --b are required", file=sys.stderr)
        return 1
    try:
        ca = int(args.candidate_a)
        cb = int(args.candidate_b)
    except ValueError:
        print("[HOLD] candidate indices must be integers", file=sys.stderr)
        return 1

    a_path = Path(args.a).expanduser().resolve()
    b_path = Path(args.b).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve() if args.out else Path.cwd() / f"{args.stage}.json"
    report: Dict[str, Any] = {
        "status": "HOLD_COMPARISON_NOT_COMPLETED",
        "stage": args.stage,
        "units": args.units,
        "a": str(a_path),
        "b": str(b_path),
        "pass": False,
        "authorizes_mapping": False,
        "authorizes_reflection": False,
        "authorizes_mesh_movement": False,
        "authorizes_C2": False,
        "authorizes_F3_4": False,
        "authorizes_Gate_D": False,
    }
    try:
        if not a_path.is_file() or not b_path.is_file():
            raise FileNotFoundError(f"Missing input: a={a_path.is_file()} b={b_path.is_file()}")
        a = load_array(a_path, args.key_a or None, ca)
        b = load_array(b_path, args.key_b or None, cb)
        direct = point_metrics(a, b)
        reflected = point_metrics(a, reflection_x(b))
        shape = shape_metrics(a, b)
        threshold_table = load_thresholds(args.thresholds or None)
        max_abs, rmse, threshold_source = infer_thresholds(args.stage, threshold_table, args.units)
        if args.max_abs is not None:
            max_abs = float(args.max_abs)
            threshold_source += "+CLI_MAX_ABS"
        if args.rmse is not None:
            rmse = float(args.rmse)
            threshold_source += "+CLI_RMSE"
        if not math.isfinite(max_abs) or not math.isfinite(rmse) or max_abs < 0 or rmse < 0:
            raise ValueError("Identity thresholds must be finite and non-negative")

        passed = passes_identity(direct, max_abs=max_abs, rmse=rmse)
        status_prefix = "PASS" if passed else "HOLD"
        report.update(
            {
                "status": f"{status_prefix}_{args.stage.upper()}",
                "pass": bool(passed),
                "hashes": {"a": sha256_file(a_path), "b": sha256_file(b_path)},
                "thresholds_used": {
                    "max_abs_coordinate_error": max_abs,
                    "rmse": rmse,
                    "source": threshold_source,
                },
                "direct": direct,
                "x_reflection_diagnostic": reflected,
                "shape": shape,
                "interpretation": (
                    "Only direct metrics decide identity. The reflected result is diagnostic only and "
                    "cannot authorize chirality changes, a reflected mesh, or a joint permutation."
                ),
            }
        )
        write_json(out_path, report)
        print(f"[{status_prefix}] {report['status']}")
        print(out_path)
        return 0 if passed else 1
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()
        write_json(out_path, report)
        print(f"[HOLD] Comparison failed: {exc}", file=sys.stderr)
        print(out_path, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
