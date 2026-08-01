#!/usr/bin/env python3
"""Print safe, compact metadata for candidate keypoint/camera artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(f"argument_error: {message}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def summarize_array(arr: np.ndarray) -> dict[str, Any]:
    arr = np.asarray(arr)
    numeric = np.issubdtype(arr.dtype, np.number)
    out: dict[str, Any] = {
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "numeric": bool(numeric),
    }
    if numeric and arr.size:
        finite = np.asarray(arr, dtype=np.float64)
        finite = finite[np.isfinite(finite)]
        out["finite_count"] = int(finite.size)
        if finite.size:
            out.update({
                "min": float(finite.min()),
                "max": float(finite.max()),
                "mean": float(finite.mean()),
            })
    return out


def inspect(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": str(path.resolve()),
        "exists": path.is_file(),
    }
    if not path.is_file():
        return record
    record["size_bytes"] = path.stat().st_size
    record["sha256"] = sha256(path)
    try:
        suffix = path.suffix.lower()
        if suffix == ".npy":
            record["array"] = summarize_array(np.load(path, allow_pickle=False))
        elif suffix == ".npz":
            pack = np.load(path, allow_pickle=False)
            record["arrays"] = {k: summarize_array(pack[k]) for k in pack.files}
        elif suffix == ".json":
            payload = json.loads(path.read_text())
            if isinstance(payload, dict):
                record["json_top_level_keys"] = sorted(payload.keys())
            else:
                record["json_type"] = type(payload).__name__
        else:
            record["note"] = "metadata only; file content not parsed"
    except Exception as error:
        record["parse_error"] = f"{type(error).__name__}: {error}"
    return record


def main() -> int:
    parser = SafeArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    records = [inspect(Path(p).expanduser()) for p in args.paths]
    text = json.dumps(records, indent=2)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n")
        print(f"[PASS] ARTIFACT_REPORT={args.out}")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as error:
        print(f"[HOLD] INSPECTION_NOT_RUN={type(error).__name__}: {error}")
        code = 0
    raise SystemExit(code)
