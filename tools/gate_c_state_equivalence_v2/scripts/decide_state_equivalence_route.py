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
        description=(
            "Route Gate C after the H0-H4 state-equivalence ladder. This router never launches optimization."
        )
    )
    p.add_argument("--contract-matrix", default="")
    p.add_argument("--h2", default="")
    p.add_argument("--h3", default="")
    p.add_argument("--h4a", default="")
    p.add_argument("--h4", default="")
    p.add_argument("--source-mapping", default="")
    p.add_argument("--producer-unresolved", action="store_true")
    p.add_argument("--out-dir", default="")
    return p.parse_known_args()


def load_optional(path: str) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(p)
    return read_json(p)


def passed(report: Optional[Dict[str, Any]]) -> bool:
    return bool(report and report.get("pass") is True)


def main() -> int:
    args, unknown = parser()
    if unknown:
        print(f"[HOLD] Unknown arguments: {unknown}", file=sys.stderr)
        return 1
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else Path.cwd() / "state_equivalence_decision"
    out_dir.mkdir(parents=True, exist_ok=True)

    decision: Dict[str, Any] = {
        "status": "HOLD_DECISION_NOT_COMPLETED",
        "reason": "",
        "authorizes_mapping": False,
        "authorizes_corrected_target": False,
        "authorizes_candidate_scoring": False,
        "authorizes_mesh_movement": False,
        "authorizes_MANO_articulation": False,
        "authorizes_C2": False,
        "authorizes_F3_4": False,
        "authorizes_Gate_D": False,
    }
    try:
        if args.producer_unresolved:
            route = "ROUTE_U_CONTAINED_STATE_LINEAGE_FAILURE"
            reason = "The exact producer or immutable active-run artifacts cannot be recovered."
        else:
            matrix = load_optional(args.contract_matrix)
            h2 = load_optional(args.h2)
            h3 = load_optional(args.h3)
            h4a = load_optional(args.h4a)
            h4 = load_optional(args.h4)
            mapping = load_optional(args.source_mapping)
            mapping_proven = bool(mapping and mapping.get("source_proven") is True)

            if matrix is None:
                route = "HOLD_BEFORE_H0_H1_CONTRACT_MATRIX"
                reason = "Historical-versus-active H0/H1 interpretation has not been supplied."
            elif matrix.get("continue_identity_ladder") is not True:
                route = matrix.get("status", "ROUTE_U_CONTAINED_STATE_LINEAGE_FAILURE")
                reason = matrix.get("reason", "H0/H1 do not establish one coherent contract.")
            elif not passed(h2):
                route = "HOLD_H2_PROJECTION_IDENTITY_FAILED_OR_MISSING"
                reason = "The exact guidance 3D-to-2D projection has not passed its frozen tolerance."
            elif not passed(h3):
                route = "HOLD_H3_SHARED_FRAME_IDENTITY_FAILED_OR_MISSING"
                reason = "The exact C1/shared-frame conversion has not passed its frozen tolerance."
            elif not passed(h4a):
                route = "HOLD_H4A_MESH_SERIALIZATION_IDENTITY_FAILED_OR_MISSING"
                reason = "The ordered 778-vertex source array has not been proven identical after mesh serialization/import."
            elif not passed(h4):
                route = "HOLD_H4_LIVE_HELPER_IDENTITY_FAILED_OR_MISSING"
                reason = "The exact zero-update mesh-derived/live-helper joints have not passed direct identity."
            else:
                route = "READY_FOR_SOURCE_VERIFIED_GATE_C0_H_CANDIDATE_AUDIT"
                reason = (
                    "H0-H4 pass under one selected contract. Physical-hand identity, handedness, and same-run candidate "
                    "selection may now be audited. Placement, articulation, C2, F3.4, and Gate D remain closed."
                )
                decision["authorizes_candidate_scoring"] = True

            if mapping_proven:
                decision["source_proven_mapping_present"] = True
                decision["mapping_note"] = (
                    "A human-authored source-proven mapping exists. It remains non-authorizing until the complete direct "
                    "identity ladder passes under the mapped contract."
                )

        decision.update({"status": route, "reason": reason})
        write_json(out_dir / "decision.json", decision)
        md = [
            "# Gate-C state-equivalence decision",
            "",
            f"**Route:** `{route}`",
            "",
            reason,
            "",
            "## Authorization state",
            "",
        ]
        for key in [
            "authorizes_mapping",
            "authorizes_corrected_target",
            "authorizes_candidate_scoring",
            "authorizes_mesh_movement",
            "authorizes_MANO_articulation",
            "authorizes_C2",
            "authorizes_F3_4",
            "authorizes_Gate_D",
        ]:
            md.append(f"- `{key}`: `{str(decision[key]).lower()}`")
        md.extend(
            [
                "",
                "The router never authorizes a reflected hand, guessed permutation, target rewrite, or optimizer launch.",
                "",
            ]
        )
        (out_dir / "decision.md").write_text("\n".join(md), encoding="utf-8")
        ready = route.startswith("READY_")
        print(f"[{'PASS' if ready else 'HOLD'}] {route}")
        print(out_dir / "decision.json")
        return 0 if ready else 1
    except Exception as exc:
        decision["error_type"] = type(exc).__name__
        decision["error"] = str(exc)
        decision["traceback"] = traceback.format_exc()
        write_json(out_dir / "decision.json", decision)
        print(f"[HOLD] Route decision failed: {exc}", file=sys.stderr)
        print(out_dir / "decision.json", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
