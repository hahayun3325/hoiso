#!/usr/bin/env python3
"""Validate a raw VLM hand-choice response against deterministic candidates.

The VLM cannot override the deterministic correspondence/provenance gate.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(f"argument_error: {message}")


ALLOWED_DECISIONS = {"select", "hold"}
ALLOWED_HANDS = {"left", "right", "uncertain"}


def main() -> int:
    parser = SafeArgumentParser()
    parser.add_argument("--raw-response", required=True, type=Path)
    parser.add_argument("--audit-summary", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    audit = json.loads(args.audit_summary.read_text())
    response = json.loads(args.raw_response.read_text())
    errors: list[str] = []

    if not isinstance(response, dict):
        errors.append("response_not_object")
        response = {}
    decision = response.get("decision")
    candidate_id = response.get("selected_candidate_id")
    physical_hand = response.get("physical_hand")
    handedness = response.get("handedness")
    confidence = response.get("confidence")
    reasons = response.get("reasons")

    if decision not in ALLOWED_DECISIONS:
        errors.append("decision_must_be_select_or_hold")
    if physical_hand != "upper":
        errors.append("physical_hand_must_be_upper")
    if handedness not in ALLOWED_HANDS:
        errors.append("handedness_invalid")
    if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
        errors.append("confidence_must_be_0_to_1")
    if not isinstance(reasons, list) or not all(isinstance(x, str) for x in reasons):
        errors.append("reasons_must_be_string_list")

    candidates = {c.get("candidate_id"): c for c in audit.get("candidates", [])}
    selected = candidates.get(candidate_id)
    if decision == "select":
        if candidate_id not in candidates:
            errors.append("selected_candidate_not_in_audit")
        elif selected.get("metadata_contract_pass") is not True:
            errors.append("vlm_cannot_select_candidate_with_failed_metadata_contract")
        elif selected.get("route") == "HOLD_REFLECTED_ONLY":
            errors.append("vlm_cannot_authorize_reflected_only_candidate")
        elif selected.get("route") == "HOLD_CANDIDATE_INVALID":
            errors.append("vlm_cannot_select_invalid_candidate")

    valid = not errors
    deterministic_route = audit.get("decision", {}).get("route")
    if not valid:
        final_route = "HOLD_INVALID_VLM_RESPONSE"
    elif decision == "hold":
        final_route = "HOLD_VLM_SEMANTIC_REVIEW"
    elif selected and selected.get("route") == "PASS_CORRESPONDENCE_CANDIDATE":
        final_route = "VLM_SUPPORTS_DETERMINISTIC_CORRESPONDENCE_CANDIDATE"
    elif selected and selected.get("route") == "FAIL_GLOBAL_CORRESPONDENCE":
        final_route = "VLM_SUPPORTS_IDENTITY_ONLY_PREPARE_ARTICULATION_REVIEW"
    else:
        final_route = "HOLD_VLM_CANNOT_OVERRIDE_DETERMINISTIC_GATE"

    output = {
        "schema_version": "gate_c_vlm_hand_choice_validation_v1",
        "raw_response_path": str(args.raw_response.resolve()),
        "audit_summary_path": str(args.audit_summary.resolve()),
        "valid": valid,
        "validation_errors": errors,
        "raw_decision": decision,
        "selected_candidate_id": candidate_id,
        "deterministic_route": deterministic_route,
        "final_route": final_route,
        "authorizations": {
            "run_optimizer": False,
            "run_c2": False,
            "run_f34": False,
            "run_gate_d": False,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2) + "\n")
    print(f"[INFO] VLM_RESPONSE_VALID={valid}")
    print(f"[INFO] FINAL_ROUTE={final_route}")
    print(f"[PASS] VALIDATION_RECORD={args.out}")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as error:
        print(f"[HOLD] VLM_VALIDATION_NOT_RUN={type(error).__name__}: {error}")
        code = 0
    raise SystemExit(code)
