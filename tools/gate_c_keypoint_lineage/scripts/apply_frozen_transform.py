#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np

from common import load_array, sha256_file, write_json


def parser() -> Tuple[argparse.Namespace, list[str]]:
    p = argparse.ArgumentParser(description="Apply one frozen 4x4 transform to keypoints; no optimization.")
    p.add_argument("--points", default="")
    p.add_argument("--key", default="")
    p.add_argument("--candidate", default="0")
    p.add_argument("--transform", default="")
    p.add_argument("--transform-key", default="")
    p.add_argument("--invert", action="store_true")
    p.add_argument("--out-dir", default="")
    return p.parse_known_args()


def load_matrix(path: Path, key: str) -> np.ndarray:
    if path.suffix.lower() == ".npy":
        x = np.load(path, allow_pickle=True)
        if isinstance(x, np.ndarray) and x.shape == () and x.dtype == object:
            x = x.item()
            if isinstance(x, dict):
                if not key:
                    raise KeyError("Transform NPY stores a dict; provide --transform-key")
                x = x[key]
    elif path.suffix.lower() == ".npz":
        z = np.load(path, allow_pickle=True)
        if not key:
            if len(z.files) != 1:
                raise KeyError(f"Transform NPZ has keys {z.files}; provide --transform-key")
            key = z.files[0]
        x = z[key]
    elif path.suffix.lower() == ".json":
        x = json.loads(path.read_text(encoding="utf-8"))
        if key:
            for part in key.split("."):
                x = x[part]
    else:
        x = np.loadtxt(path)
    x = np.asarray(x, dtype=np.float64)
    while x.ndim > 2 and x.shape[0] == 1:
        x = x[0]
    if x.shape != (4, 4):
        raise ValueError(f"Expected 4x4 transform, got {x.shape}")
    return x


def main() -> int:
    args, unknown = parser()
    if unknown:
        print(f"[HOLD] Unknown arguments: {unknown}", file=sys.stderr)
        return 1
    if not args.points or not args.transform:
        print("[HOLD] --points and --transform are required", file=sys.stderr)
        return 1
    try:
        candidate = int(args.candidate)
    except ValueError:
        print("[HOLD] --candidate must be an integer", file=sys.stderr)
        return 1
    points_path = Path(args.points).expanduser().resolve()
    transform_path = Path(args.transform).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else Path.cwd() / "frozen_transform"
    out_dir.mkdir(parents=True, exist_ok=True)
    report: Dict[str, Any] = {
        "status": "HOLD_TRANSFORM_NOT_COMPLETED",
        "authorizes_mesh_movement": False,
    }
    try:
        p = load_array(points_path, args.key or None, candidate)
        if p.shape[1] != 3:
            raise ValueError(f"Expected Nx3 points, got {p.shape}")
        T = load_matrix(transform_path, args.transform_key)
        if args.invert:
            T = np.linalg.inv(T)
        ph = np.concatenate([p, np.ones((len(p), 1), dtype=np.float64)], axis=1)
        out = (T @ ph.T).T[:, :3]
        np.save(out_dir / "transformed_points.npy", out)
        np.save(out_dir / "transform_used.npy", T)
        report.update(
            {
                "status": "PASS_FROZEN_TRANSFORM_APPLIED",
                "points_sha256": sha256_file(points_path),
                "transform_sha256": sha256_file(transform_path),
                "inverted": bool(args.invert),
                "point_count": int(len(p)),
                "note": "This is a deterministic coordinate conversion only; it does not fit or optimize a transform.",
            }
        )
        write_json(out_dir / "report.json", report)
        print("[PASS] Frozen transform applied")
        print(out_dir / "transformed_points.npy")
        return 0
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()
        write_json(out_dir / "report.json", report)
        print(f"[HOLD] Frozen transform failed: {exc}", file=sys.stderr)
        print(out_dir / "report.json", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
