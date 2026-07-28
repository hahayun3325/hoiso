#!/usr/bin/env python3
"""Validate a blind VLM critic response and deterministically select a candidate.

Usage:
  python3 select_candidate_from_critic.py BANK_SUMMARY.json CRITIC_RESPONSE.json OUTPUT_DIR

Only candidates that pass both deterministic and semantic gates are eligible.
The local router—not the VLM's preferred ID—makes the final selection.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import shlex
import sys
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if len(sys.argv) != 4:
        print("[HOLD] CRITIC_SELECTION_USAGE=BANK_SUMMARY.json CRITIC_RESPONSE.json OUTPUT_DIR")
        return

    bank_path = Path(sys.argv[1])
    response_path = Path(sys.argv[2])
    out_dir = Path(sys.argv[3])
    if not bank_path.is_file() or not response_path.is_file():
        print(
            "[HOLD] CRITIC_SELECTION_INPUT_MISSING="
            f"bank={bank_path.is_file()} response={response_path.is_file()}"
        )
        return

    try:
        bank = json.loads(bank_path.read_text(encoding="utf-8"))
        response = json.loads(response_path.read_text(encoding="utf-8").strip())
    except Exception as error:
        print(f"[HOLD] CRITIC_SELECTION_JSON_INVALID={type(error).__name__}: {error}")
        return

    required_top = {
        "schema_version",
        "case_id",
        "uncertain",
        "candidate_reviews",
        "notes",
    }
    missing_top = sorted(required_top - set(response.keys()))
    if missing_top:
        print("[HOLD] CRITIC_RESPONSE_TOP_KEYS_MISSING=" + ",".join(missing_top))
        return
    if response.get("schema_version") != "auto_v2_candidate_critic_v1":
        print(f"[HOLD] CRITIC_RESPONSE_SCHEMA={response.get('schema_version')}")
        return
    if response.get("case_id") != bank.get("case_id"):
        print("[HOLD] CRITIC_RESPONSE_CASE_MISMATCH")
        return
    if response.get("uncertain") is not False:
        print("[HOLD] CRITIC_RESPONSE_UNCERTAIN=true")
        return

    bank_candidates = {item["candidate_id"]: item for item in bank.get("candidates", [])}
    reviews = response.get("candidate_reviews")
    if not isinstance(reviews, list):
        print("[HOLD] CRITIC_RESPONSE_REVIEWS_NOT_LIST")
        return

    required_review_keys = {
        "candidate_id",
        "target_identity_preserved",
        "lid_complete",
        "base_complete",
        "hinge_preserved",
        "support_absent",
        "tabletop_absent",
        "hand_absent",
        "orientation_preserved",
        "safe_for_hunyuan",
        "confidence",
        "failure_reasons",
    }
    seen: set[str] = set()
    eligible: list[tuple[float, str, dict[str, Any]]] = []
    validation_errors: list[str] = []

    for review in reviews:
        if not isinstance(review, dict):
            validation_errors.append("review_not_object")
            continue
        missing = sorted(required_review_keys - set(review.keys()))
        candidate_id = str(review.get("candidate_id", ""))
        if missing:
            validation_errors.append(f"{candidate_id}:missing:{'|'.join(missing)}")
            continue
        if candidate_id not in bank_candidates:
            validation_errors.append(f"{candidate_id}:unknown")
            continue
        if candidate_id in seen:
            validation_errors.append(f"{candidate_id}:duplicate")
            continue
        seen.add(candidate_id)
        try:
            confidence = float(review["confidence"])
        except (TypeError, ValueError):
            validation_errors.append(f"{candidate_id}:confidence")
            continue
        if not (0.0 <= confidence <= 1.0):
            validation_errors.append(f"{candidate_id}:confidence_range")
            continue
        failures = review.get("failure_reasons")
        if not isinstance(failures, list):
            validation_errors.append(f"{candidate_id}:failure_reasons")
            continue

        semantic_bools = [
            "target_identity_preserved",
            "lid_complete",
            "base_complete",
            "hinge_preserved",
            "support_absent",
            "tabletop_absent",
            "hand_absent",
            "orientation_preserved",
            "safe_for_hunyuan",
        ]
        bool_valid = all(review.get(key) is True for key in semantic_bools)
        deterministic_pass = bool(bank_candidates[candidate_id].get("deterministic_gate_pass"))
        if deterministic_pass and bool_valid and confidence >= 0.80 and not failures:
            eligible.append((confidence, candidate_id, review))

    expected_ids = set(bank_candidates)
    if seen != expected_ids:
        validation_errors.append("review_id_set_mismatch")
    if validation_errors:
        print("[HOLD] CRITIC_RESPONSE_VALIDATION=" + ",".join(validation_errors))
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    selection_path = out_dir / "selection.json"
    env_path = out_dir / "selected_candidate.env"
    if selection_path.exists() or env_path.exists():
        print(f"[HOLD] CRITIC_SELECTION_OUTPUT_EXISTS={out_dir}")
        return

    if not eligible:
        record = {
            "schema_version": "auto_v2_selection_v1",
            "case_id": bank.get("case_id"),
            "decision": "hold_no_eligible_candidate",
            "selected_candidate_id": None,
            "authorize_hunyuan": False,
            "bank_sha256": digest(bank_path),
            "critic_response_sha256": digest(response_path),
        }
        selection_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        env_path.write_text(
            "AUTO_V2_SELECTED='0'\n"
            "AUTO_V2_SELECTION_REASON='no_eligible_candidate'\n",
            encoding="utf-8",
        )
        print(f"[HOLD] AUTO_V2_NO_ELIGIBLE_CANDIDATE={selection_path}")
        return

    eligible.sort(key=lambda item: (-item[0], item[1]))
    confidence, candidate_id, review = eligible[0]
    candidate = bank_candidates[candidate_id]
    candidate_dir = Path(candidate["candidate_dir"])
    manifest_path = Path(candidate["manifest"])
    rgb_path = Path(candidate["hunyuan_input_rgb"])
    if not candidate_dir.is_dir() or not manifest_path.is_file() or not rgb_path.is_file():
        print("[HOLD] CRITIC_SELECTION_CANDIDATE_ASSET_MISSING")
        return

    record = {
        "schema_version": "auto_v2_selection_v1",
        "case_id": bank.get("case_id"),
        "decision": "selected_for_existing_provenance_guard",
        "selected_candidate_id": candidate_id,
        "critic_confidence": confidence,
        "authorize_hunyuan": False,
        "authorization_note": (
            "This is only preselection. Existing exact-file provenance and authorization "
            "scripts must still pass before Hunyuan."
        ),
        "candidate_dir": str(candidate_dir),
        "candidate_manifest": str(manifest_path),
        "candidate_rgb": str(rgb_path),
        "candidate_rgb_sha256": digest(rgb_path),
        "bank_sha256": digest(bank_path),
        "critic_response_sha256": digest(response_path),
        "critic_review": review,
    }
    selection_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    env_lines = [
        "AUTO_V2_SELECTED='1'",
        f"AUTO_V2_SELECTED_ID={shlex.quote(candidate_id)}",
        f"AUTO_V2_SELECTED_DIR={shlex.quote(str(candidate_dir))}",
        f"AUTO_V2_SELECTED_MANIFEST={shlex.quote(str(manifest_path))}",
        f"AUTO_V2_SELECTED_RGB={shlex.quote(str(rgb_path))}",
        f"AUTO_V2_CRITIC_CONFIDENCE={shlex.quote(str(confidence))}",
    ]
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    print(f"[PASS] AUTO_V2_PRESELECTED={candidate_id}")
    print(f"[PASS] AUTO_V2_SELECTION_ENV={env_path}")


if __name__ == "__main__":
    main()
