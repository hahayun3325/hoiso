#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def shape_of(value: Any) -> list[int] | None:
    try:
        return list(np.asarray(value).shape)
    except Exception:
        return None


def load_payload(path: Path) -> Any:
    data = np.load(path, allow_pickle=True)
    if isinstance(data, np.ndarray) and data.shape == ():
        return data.item()
    return data


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    if not args.root.is_dir():
        raise SystemExit(f"HaMeR root is not a directory: {args.root}")

    reports: list[dict[str, Any]] = []
    for path in sorted(args.root.rglob("*.npy")):
        item: dict[str, Any] = {
            "path": str(path),
            "sha256": sha256(path),
        }
        try:
            payload = load_payload(path)
            if isinstance(payload, dict):
                shapes = {str(k): shape_of(v) for k, v in payload.items()}
                candidate_counts = {
                    k: s[0]
                    for k, s in shapes.items()
                    if s is not None and len(s) >= 1 and s[0] > 0
                }
                item.update({
                    "payload_type": "dict",
                    "keys": sorted(shapes),
                    "shapes": shapes,
                    "candidate_count_hypotheses": candidate_counts,
                })
            else:
                item.update({
                    "payload_type": type(payload).__name__,
                    "shape": shape_of(payload),
                })
        except Exception as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
        reports.append(item)

    result = {
        "schema": "same_run_hamer_batch_inventory_v99_11",
        "root": str(args.root),
        "files": reports,
        "policy": "Do not assume candidate 0. Resolve selected index from source lineage.",
        "authorizes_optimizer": False,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[PASS] WROTE={args.out}")
    print(f"[INFO] NPY_FILES={len(reports)}")


if __name__ == "__main__":
    main()
