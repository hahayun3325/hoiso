#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np


def run(cmd: list[str], expect: int = 0) -> None:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != expect:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nreturn={proc.returncode} expected={expect}\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}"
        )


def write_h01(path: Path, passed: bool) -> None:
    payload = {
        "status": "PASS_H0_H1_CONTINUE_TO_H2" if passed else "HOLD_H0_RAW_JOINT_IDENTITY_FAILED",
        "H0": {"pass": passed},
        "H1": {"internal_handedness_pass": passed, "guidance_pass": passed},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    scripts = root / "scripts"
    thresholds = root / "config/state_equivalence_thresholds.json"
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        a = np.arange(63, dtype=np.float64).reshape(21, 3) / 1000.0
        b = a.copy()
        np.save(d / "a.npy", a)
        np.save(d / "b.npy", b)
        run(
            [
                sys.executable,
                str(scripts / "compare_keypoint_arrays.py"),
                "--a",
                str(d / "a.npy"),
                "--b",
                str(d / "b.npy"),
                "--stage",
                "H3_shared_frame_identity",
                "--units",
                "m",
                "--thresholds",
                str(thresholds),
                "--out",
                str(d / "h3.json"),
            ]
        )
        write_h01(d / "hist.json", True)
        write_h01(d / "active.json", False)
        run(
            [
                sys.executable,
                str(scripts / "summarize_contract_matrix.py"),
                "--historical",
                str(d / "hist.json"),
                "--active",
                str(d / "active.json"),
                "--out-dir",
                str(d / "matrix"),
            ]
        )
        for name in ["h2", "h4a", "h4"]:
            (d / f"{name}.json").write_text(json.dumps({"pass": True}), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "decide_state_equivalence_route.py"),
                "--contract-matrix",
                str(d / "matrix/contract_matrix.json"),
                "--h2",
                str(d / "h2.json"),
                "--h3",
                str(d / "h3.json"),
                "--h4a",
                str(d / "h4a.json"),
                "--h4",
                str(d / "h4.json"),
                "--out-dir",
                str(d / "decision"),
            ]
        )
        decision = json.loads((d / "decision/decision.json").read_text(encoding="utf-8"))
        assert decision["status"] == "READY_FOR_SOURCE_VERIFIED_GATE_C0_H_CANDIDATE_AUDIT"
        assert decision["authorizes_candidate_scoring"] is True
        assert decision["authorizes_mesh_movement"] is False
    print("[PASS] synthetic state-equivalence smoke test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
