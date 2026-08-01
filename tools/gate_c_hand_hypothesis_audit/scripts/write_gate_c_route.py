#!/usr/bin/env python3
"""Write the non-authorizing professor route after the hand-candidate audit."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(f"argument_error: {message}")


def bind(path: Path | None) -> dict:
    if path is None:
        return {"missing": True}
    path = path.expanduser().resolve()
    if not path.is_file():
        return {"path": str(path), "missing": True}
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }


def main() -> int:
    parser = SafeArgumentParser()
    parser.add_argument("--audit-summary", required=True, type=Path)
    parser.add_argument("--vlm-validation", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    audit = json.loads(args.audit_summary.read_text())
    audit_decision = audit.get("decision", {})
    audit_route = audit_decision.get("route")
    selected = audit_decision.get("selected_candidate_id")

    vlm = None
    if args.vlm_validation and args.vlm_validation.is_file():
        vlm = json.loads(args.vlm_validation.read_text())

    if audit_route == "SELECT_CORRESPONDENCE_CANDIDATE_FOR_C1_5":
        if vlm is None:
            route = "HOLD_OPTIONAL_SEMANTIC_REVIEW_OR_PROCEED_WITH_DETERMINISTIC_SELECTION"
        elif vlm.get("final_route") == "VLM_SUPPORTS_DETERMINISTIC_CORRESPONDENCE_CANDIDATE":
            route = "PREPARE_SELECTED_CANDIDATE_SHARED_FRAME_DRY_RUN"
        else:
            route = "HOLD_VLM_AND_DETERMINISTIC_SELECTION_DISAGREE"
    elif audit_route == "PREPARE_BOUNDED_ARTICULATION_METHOD_DECISION":
        if vlm is None or vlm.get("final_route") in {
            "VLM_SUPPORTS_IDENTITY_ONLY_PREPARE_ARTICULATION_REVIEW",
            "HOLD_VLM_SEMANTIC_REVIEW",
        }:
            route = "PREPARE_ONE_BOUNDED_SELECTED_JOINT_MANO_BRANCH"
        else:
            route = "HOLD_ARTICULATION_UNTIL_SEMANTIC_IDENTITY_REVIEW"
    elif audit_route == "HOLD_AUDIT_CHIRALITY_OR_RASTER_CONTRACT":
        route = "REPAIR_SOURCE_RASTER_OR_HANDEDNESS_METADATA_DO_NOT_REFLECT_3D_HAND"
    else:
        route = "FREEZE_GATE_C_OR_FIND_SOURCE_VERIFIED_UPPER_HAND_CANDIDATE"

    record = {
        "schema_version": "gate_c_professor_route_v1",
        "case_id": "alapuse02v3n60",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "audit_route": audit_route,
        "selected_candidate_id": selected,
        "professor_route": route,
        "reasoning": [
            "translation-only Branch E is permanently closed",
            "proper-root and reflected-only Branch F recovery are closed",
            "object-root movement cannot repair a hand-only keypoint correspondence failure",
            "contact/collision stages remain closed until a credible hand projection exists",
        ],
        "bound_inputs": {
            "audit_summary": bind(args.audit_summary),
            "vlm_validation": bind(args.vlm_validation),
        },
        "authorizations": {
            "run_new_optimizer": False,
            "run_c2": False,
            "run_f34": False,
            "run_gate_d": False,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        print(f"[HOLD] ROUTE_ALREADY_EXISTS={args.out}")
        return 0
    args.out.write_text(json.dumps(record, indent=2) + "\n")
    print(f"[INFO] PROFESSOR_ROUTE={route}")
    print(f"[PASS] ROUTE_RECORD={args.out}")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as error:
        print(f"[HOLD] ROUTE_NOT_WRITTEN={type(error).__name__}: {error}")
        code = 0
    raise SystemExit(code)
