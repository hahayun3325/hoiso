#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from common import read_json, write_json


def parser() -> Tuple[argparse.Namespace, list[str]]:
    p = argparse.ArgumentParser(
        description="Interpret historical-versus-active H0/H1 reports without rewriting any target."
    )
    p.add_argument("--historical", default="")
    p.add_argument("--active", default="")
    p.add_argument("--buffer-comparison", default="")
    p.add_argument("--out-dir", default="")
    return p.parse_known_args()


def load_optional(path: str) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(p)
    return read_json(p)


def stage_state(report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if report is None:
        return {"available": False, "h0": False, "h1_internal": False, "h1_guidance": False, "all": False}
    h0 = report.get("H0", {}).get("pass") is True
    h1i = report.get("H1", {}).get("internal_handedness_pass") is True
    h1g_raw = report.get("H1", {}).get("guidance_pass")
    h1g = h1g_raw is True or h1g_raw is None
    return {
        "available": True,
        "h0": h0,
        "h1_internal": h1i,
        "h1_guidance": h1g,
        "all": bool(h0 and h1i and h1g),
        "status": report.get("status"),
        "recommended_route": report.get("recommended_route"),
    }


def main() -> int:
    args, unknown = parser()
    if unknown:
        print(f"[HOLD] Unknown arguments: {unknown}", file=sys.stderr)
        return 1
    if not args.historical or not args.active:
        print("[HOLD] --historical and --active are required", file=sys.stderr)
        return 1
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else Path.cwd() / "contract_matrix"
    out_dir.mkdir(parents=True, exist_ok=True)
    result: Dict[str, Any] = {
        "status": "HOLD_CONTRACT_MATRIX_NOT_COMPLETED",
        "continue_identity_ladder": False,
        "selected_contract_for_historical_run": None,
        "authorizes_target_rewrite": False,
        "authorizes_candidate_scoring": False,
        "authorizes_mesh_movement": False,
    }
    try:
        historical_report = load_optional(args.historical)
        active_report = load_optional(args.active)
        buffers = load_optional(args.buffer_comparison)
        hs = stage_state(historical_report)
        ac = stage_state(active_report)
        buffers_equal = bool(buffers and buffers.get("pass") is True)

        if hs["all"] and ac["all"]:
            if buffers_equal:
                status = "PASS_BOTH_CONTRACTS_REPRODUCE_RUN_AND_BUFFERS_EQUIVALENT"
                reason = "Historical and active contracts reproduce H0/H1 and their stored buffers are equivalent."
            else:
                status = "PASS_HISTORICAL_AND_ACTIVE_REPRODUCE_RUN_BUT_VERSION_EQUIVALENCE_UNPROVEN"
                reason = (
                    "Both contracts reproduce this saved candidate, but full buffer equivalence is absent or failed. "
                    "Use the historical contract for historical-run lineage; treat the active contract as a separate version."
                )
            selected = "historical"
            continue_ladder = True
        elif hs["all"] and not ac["all"]:
            status = "PASS_HISTORICAL_CONTRACT_ONLY_VERSION_DRIFT_DETECTED"
            reason = (
                "The historical contract reproduces the saved run but the active contract does not. Preserve the historical "
                "branch immutably; either reconstruct its dependencies or rerun HaMeR under the active contract as a new branch."
            )
            selected = "historical"
            continue_ladder = True
        elif ac["all"] and not hs["all"]:
            status = "PASS_ACTIVE_CONTRACT_ONLY_HISTORICAL_REGRESSOR_STALE_OR_UNRELATED"
            reason = (
                "The active contract reproduces the saved batch while the historical J-regressor contract does not. "
                "Quarantine the historical file and regenerate all hand-derived artifacts in a new active-contract branch."
            )
            selected = "active"
            continue_ladder = True
        else:
            status = "HOLD_BOTH_CONTRACTS_FAIL_SOURCE_OR_PROVENANCE_MISMATCH"
            reason = (
                "Neither contract proves H0/H1 for one coherent saved candidate. Recover candidate/run/checkpoint/MANO/handedness "
                "provenance before H2."
            )
            selected = None
            continue_ladder = False

        result.update(
            {
                "status": status,
                "reason": reason,
                "historical": hs,
                "active": ac,
                "buffer_comparison_pass": buffers_equal if buffers is not None else None,
                "selected_contract_for_historical_run": selected,
                "continue_identity_ladder": continue_ladder,
                "next_action": (
                    "Continue H2-H4 using only the selected contract and artifacts derived from the same run."
                    if continue_ladder
                    else "Stop before H2 and recover source/provenance or close Route U."
                ),
            }
        )
        write_json(out_dir / "contract_matrix.json", result)
        md = [
            "# Historical-versus-active contract decision",
            "",
            f"**Status:** `{status}`",
            "",
            reason,
            "",
            f"- selected contract for the historical run: `{selected}`",
            f"- continue H2-H4: `{str(continue_ladder).lower()}`",
            "- target rewrite authorized: `false`",
            "- candidate scoring authorized: `false`",
            "- mesh movement authorized: `false`",
            "",
        ]
        (out_dir / "contract_matrix.md").write_text("\n".join(md), encoding="utf-8")
        print(f"[{'PASS' if continue_ladder else 'HOLD'}] {status}")
        print(out_dir / "contract_matrix.json")
        return 0 if continue_ladder else 1
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()
        write_json(out_dir / "contract_matrix.json", result)
        print(f"[HOLD] Contract matrix failed: {exc}", file=sys.stderr)
        print(out_dir / "contract_matrix.json", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
