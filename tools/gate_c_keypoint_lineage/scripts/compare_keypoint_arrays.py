#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Tuple

from common import (
    load_array,
    point_metrics,
    reflection_x,
    sha256_file,
    shape_metrics,
    write_json,
)


def parser() -> Tuple[argparse.Namespace, list[str]]:
    p = argparse.ArgumentParser(description="Compare two frozen keypoint arrays without authorizing a transform.")
    p.add_argument("--a", default="")
    p.add_argument("--b", default="")
    p.add_argument("--key-a", default="")
    p.add_argument("--key-b", default="")
    p.add_argument("--candidate-a", default="0")
    p.add_argument("--candidate-b", default="0")
    p.add_argument("--stage", default="unspecified_identity_stage")
    p.add_argument("--units", default="unspecified")
    p.add_argument("--out", default="")
    return p.parse_known_args()


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
        "authorizes_mapping": False,
        "authorizes_reflection": False,
        "authorizes_mesh_movement": False,
    }
    try:
        if not a_path.is_file() or not b_path.is_file():
            raise FileNotFoundError(f"Missing input: a={a_path.is_file()} b={b_path.is_file()}")
        a = load_array(a_path, args.key_a or None, ca)
        b = load_array(b_path, args.key_b or None, cb)
        direct = point_metrics(a, b)
        reflected = point_metrics(a, reflection_x(b))
        shape = shape_metrics(a, b)
        report.update(
            {
                "status": "PASS_DIAGNOSTIC_COMPARISON_WRITTEN",
                "hashes": {"a": sha256_file(a_path), "b": sha256_file(b_path)},
                "direct": direct,
                "x_reflection_diagnostic": reflected,
                "shape": shape,
                "interpretation": (
                    "Use direct metrics for identity. The reflected result is diagnostic only and cannot authorize chirality changes."
                ),
            }
        )
        write_json(out_path, report)
        print("[PASS] Diagnostic comparison written")
        print(out_path)
        return 0
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
