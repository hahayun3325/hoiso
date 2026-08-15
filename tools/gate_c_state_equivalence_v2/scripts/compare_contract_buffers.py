#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np

from common import sha256_file, to_numpy, write_json

DEFAULT_TIPS = np.array([744, 320, 443, 554, 671], dtype=np.int64)
DEFAULT_MAP = np.array(
    [0, 13, 14, 15, 16, 1, 2, 3, 17, 4, 5, 6, 18, 10, 11, 12, 19, 7, 8, 9, 20],
    dtype=np.int64,
)


def parser() -> Tuple[argparse.Namespace, list[str]]:
    p = argparse.ArgumentParser(description="Compare a historical J-regressor contract with active HaMeR buffers.")
    p.add_argument("--historical-j-regressor", default="")
    p.add_argument("--active-contract-npz", default="")
    p.add_argument("--atol", type=float, default=1e-8)
    p.add_argument("--out", default="")
    return p.parse_known_args()


def load_pt(path: Path) -> np.ndarray:
    import torch

    return np.asarray(to_numpy(torch.load(path, map_location="cpu")))


def array_report(a: np.ndarray, b: np.ndarray, atol: float) -> Dict[str, Any]:
    a = np.asarray(a)
    b = np.asarray(b)
    if a.shape != b.shape:
        return {"pass": False, "shape_match": False, "shape_a": list(a.shape), "shape_b": list(b.shape)}
    if np.issubdtype(a.dtype, np.integer) and np.issubdtype(b.dtype, np.integer):
        equal = bool(np.array_equal(a, b))
        return {"pass": equal, "shape_match": True, "exact_equal": equal}
    delta = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    max_abs = float(np.abs(delta).max()) if delta.size else 0.0
    rmse = float(np.sqrt(np.mean(delta * delta))) if delta.size else 0.0
    return {
        "pass": bool(max_abs <= atol),
        "shape_match": True,
        "max_abs": max_abs,
        "rmse": rmse,
        "atol": float(atol),
    }


def main() -> int:
    args, unknown = parser()
    if unknown:
        print(f"[HOLD] Unknown arguments: {unknown}", file=sys.stderr)
        return 1
    if not args.historical_j_regressor or not args.active_contract_npz:
        print("[HOLD] --historical-j-regressor and --active-contract-npz are required", file=sys.stderr)
        return 1

    hist_path = Path(args.historical_j_regressor).expanduser().resolve()
    active_path = Path(args.active_contract_npz).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve() if args.out else Path.cwd() / "contract_buffer_comparison.json"
    report: Dict[str, Any] = {
        "status": "HOLD_CONTRACT_BUFFER_COMPARISON_NOT_COMPLETED",
        "pass": False,
        "historical_j_regressor": str(hist_path),
        "active_contract_npz": str(active_path),
    }
    try:
        if not hist_path.is_file() or not active_path.is_file():
            raise FileNotFoundError(f"historical={hist_path.is_file()} active={active_path.is_file()}")
        active = np.load(active_path, allow_pickle=True)
        required = ["J_regressor", "extra_joints_idxs", "joint_map"]
        missing = [k for k in required if k not in active.files]
        if missing:
            raise KeyError(f"Active contract missing keys {missing}; available={active.files}")
        hist_j = load_pt(hist_path)
        checks = {
            "J_regressor": array_report(hist_j, active["J_regressor"], args.atol),
            "extra_joints_idxs": array_report(DEFAULT_TIPS, active["extra_joints_idxs"], 0.0),
            "joint_map": array_report(DEFAULT_MAP, active["joint_map"], 0.0),
        }
        if "joint_regressor_extra" in active.files:
            checks["joint_regressor_extra"] = {
                "pass": False,
                "present_only_in_active": True,
                "note": "Historical single-file contract does not encode the optional extra regressor.",
            }
        passed = all(v.get("pass") is True for v in checks.values())
        report.update(
            {
                "status": "PASS_CONTRACT_BUFFERS_EQUIVALENT" if passed else "HOLD_CONTRACT_BUFFERS_DIFFER",
                "pass": passed,
                "hashes": {
                    "historical_j_regressor": sha256_file(hist_path),
                    "active_contract_npz": sha256_file(active_path),
                },
                "checks": checks,
                "note": (
                    "A difference is version/provenance evidence. It does not by itself prove which contract is correct "
                    "for a historical saved batch; H0/H1 decide whether each contract reproduces that batch."
                ),
            }
        )
        write_json(out_path, report)
        print(f"[{'PASS' if passed else 'HOLD'}] {report['status']}")
        print(out_path)
        return 0 if passed else 1
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()
        write_json(out_path, report)
        print(f"[HOLD] Contract comparison failed: {exc}", file=sys.stderr)
        print(out_path, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
