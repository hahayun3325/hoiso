#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if not args.manifest.is_file():
        raise FileNotFoundError(args.manifest)

    rows: list[dict[str, Any]] = []
    with args.manifest.open(newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "candidate_uid",
            "vertices_path",
            "joints_path",
            "projected_keypoints_path",
            "reanchor_json_path",
            "metric_record_path",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing manifest columns: {sorted(missing)}")
        for raw in reader:
            record: dict[str, Any] = {"candidate_uid": raw["candidate_uid"]}
            for key in sorted(required - {"candidate_uid"}):
                value = raw.get(key, "").strip()
                path = Path(value) if value else None
                record[key] = {
                    "path": value or None,
                    "exists": bool(path and path.is_file()),
                    "sha256": sha256(path) if path else None,
                }
            rows.append(record)

    def uniqueness(key: str) -> dict[str, Any]:
        hashes = [r[key]["sha256"] for r in rows if r[key]["sha256"]]
        return {
            "available": len(hashes),
            "unique_hashes": len(set(hashes)),
            "all_available_distinct": bool(hashes) and len(set(hashes)) == len(hashes),
        }

    result = {
        "schema": "candidate_binding_audit_v99_11_7_9_21_7_12",
        "candidate_count": len(rows),
        "records": rows,
        "uniqueness": {
            key: uniqueness(key)
            for key in (
                "vertices_path",
                "joints_path",
                "projected_keypoints_path",
                "reanchor_json_path",
                "metric_record_path",
            )
        },
        "interpretation": {
            "shared_vertices_warning": (
                "If per-candidate vertices are expected but hashes are identical, inspect analyzer binding before interpreting invariant metrics."
            ),
            "shared_metric_record_warning": (
                "A common metric record across candidate UIDs may indicate a family-level metric or an input-binding error."
            ),
            "authorizes_optimizer": False,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(f"[PASS] OUT={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
