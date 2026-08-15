#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED_ROUTE = "close_combined_translation_articulation_capacity_select_next_family"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--route", required=True)
    parser.add_argument("--review", required=True)
    parser.add_argument("--capacity-report", required=True)
    parser.add_argument("--predicted", required=True)
    parser.add_argument("--deltas", required=True)
    parser.add_argument("--jacobians", required=True)
    parser.add_argument("--column-bounds", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    paths = {name: Path(value) for name, value in vars(args).items() if name != "out"}
    missing = [str(path) for path in paths.values() if not path.is_file() or path.stat().st_size == 0]
    report: dict[str, Any] = {
        "schema": "v87_input_verification_for_v88",
        "status": "HOLD" if missing else "PASS",
        "missing": missing,
        "expected_route": EXPECTED_ROUTE,
        "route_decision": None,
        "hashes": {},
        "authorizes_optimizer": False,
    }

    if not missing:
        try:
            route = read_json(paths["route"])
            report["route_decision"] = route.get("decision")
            if report["route_decision"] != EXPECTED_ROUTE:
                report["status"] = "HOLD"
                report["route_mismatch"] = True
            for name, path in paths.items():
                report["hashes"][name] = {"path": str(path), "sha256": sha256(path)}
        except Exception as error:  # fail closed, but keep a readable report
            report["status"] = "HOLD"
            report["error"] = f"{type(error).__name__}: {error}"

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"[{report['status']}] V87_INPUT_VERIFICATION={out}")


if __name__ == "__main__":
    main()
