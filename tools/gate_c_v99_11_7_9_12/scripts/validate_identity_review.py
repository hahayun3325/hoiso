#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

FIELDS = (
    "physical_hand_match",
    "laterality_plausible",
    "wrist_palm_orientation_plausible",
    "visible_finger_chain_plausible",
    "reject",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    review_path = Path(args.review)
    out_path = Path(args.out)
    if not review_path.is_file():
        print(f"[HOLD] REVIEW_MISSING={review_path}")
        return 0

    data = json.loads(review_path.read_text())
    rows = list(data.get("rows", []))
    if not rows:
        print("[HOLD] REVIEW_ROWS_EMPTY")
        return 0

    incomplete: list[str] = []
    valid: list[str] = []
    rejected: list[dict] = []

    for row in rows:
        uid = str(row.get("candidate_uid", ""))
        if not uid or any(not isinstance(row.get(field), bool) for field in FIELDS):
            incomplete.append(uid or "<missing_uid>")
            continue
        semantic_ok = all(bool(row[field]) for field in FIELDS[:-1]) and not bool(row["reject"])
        if semantic_ok:
            valid.append(uid)
        else:
            rejected.append({"candidate_uid": uid, "reason": str(row.get("reason", ""))})

    if incomplete:
        route = "hold_complete_identity_review_v99_11_7_9_12"
    elif len(valid) == 0:
        route = "close_v6_multicrop_family_no_identity_valid_survivor"
    elif len(valid) == 1:
        route = "prepare_complete_v6_selector_freeze_single_identity_survivor"
    else:
        route = "prepare_v99_11_7_9_13_deterministic_anchor_consensus_selector"

    packet = {
        "schema": "indexed_identity_review_validation_v99_11_7_9_12",
        "decision": route,
        "review_count": len(rows),
        "identity_valid_count": len(valid),
        "identity_valid_survivors": valid,
        "rejected": rejected,
        "incomplete": incomplete,
        "authorizes_v3_execution": False,
        "authorizes_optimizer": False,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(packet, indent=2) + "\n")
    print(f"[PASS] OUTPUT={out_path}")
    print(f"[INFO] DECISION={route}")
    print(f"[INFO] IDENTITY_VALID={valid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
