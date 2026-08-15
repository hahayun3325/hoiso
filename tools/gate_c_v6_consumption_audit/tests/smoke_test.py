#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLASSIFIER = ROOT / "scripts/classify_v6_control.py"
FIELDS = [
    "stage", "term", "role", "active", "representation", "tensor_name",
    "producer", "source_evidence", "artifact_path", "review_status", "notes",
]


def run_case(name: str, representations: list[str], expected: str) -> None:
    with tempfile.TemporaryDirectory(prefix=f"v6audit_{name}_") as tmp:
        tmp_path = Path(tmp)
        manifest = tmp_path / "manifest.csv"
        out = tmp_path / "out"
        with manifest.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            for index, rep in enumerate(representations):
                writer.writerow(
                    {
                        "stage": "Gate_D",
                        "term": f"term_{index}",
                        "role": "acceptance",
                        "active": "true",
                        "representation": rep,
                        "tensor_name": f"tensor_{index}",
                        "producer": f"producer_{index}",
                        "source_evidence": f"source.py:{10 + index}",
                        "artifact_path": "",
                        "review_status": "confirmed",
                        "notes": "synthetic smoke test",
                    }
                )
        proc = subprocess.run(
            [sys.executable, str(CLASSIFIER), "--manifest", str(manifest), "--out-dir", str(out)],
            check=True,
            text=True,
            capture_output=True,
        )
        decision = json.loads((out / "v6_consumption_decision.json").read_text())
        actual = decision["route"]
        if actual != expected:
            raise AssertionError(f"{name}: expected {expected}, got {actual}\n{proc.stdout}")


def main() -> None:
    run_case(
        "canonical",
        ["canonical_21j", "saved_2d_target"],
        "V6_DISCRIMINATES_CANONICAL_JOINT_CONSUMPTION",
    )
    run_case(
        "mesh",
        ["mesh_helper_21j", "saved_2d_target"],
        "V6_DISCRIMINATES_MESH_HELPER_JOINT_CONSUMPTION",
    )
    run_case(
        "mixed",
        ["canonical_21j", "mesh_helper_21j"],
        "V6_MIXED_JOINT_CONSUMPTION_REQUIRES_TERM_SPLIT",
    )
    run_case(
        "nondiscriminating",
        ["direct_fingertip_vertices", "mesh_vertices", "object_surface"],
        "V6_FUNCTIONAL_CONTROL_ONLY_NONDISCRIMINATING",
    )
    print("[PASS] v6 consumption audit smoke tests")


if __name__ == "__main__":
    main()
