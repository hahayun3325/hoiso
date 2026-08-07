#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--metrics", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()

    data = json.loads(args.metrics.read_text())
    passed = [r for r in data.get("results", []) if r.get("gate_pass")]

    if len(passed) == 0:
        decision = "close_gate_c_or_open_separate_upstream_hand_rerun_v99_12"
        selected = None
    elif len(passed) == 1:
        decision = "prepare_fresh_candidate_specific_hand_anchor_policy_v99_13"
        selected = passed[0]["candidate_uid"]
    else:
        decision = "run_indexed_vlm_critic_then_select_exactly_one_candidate_v99_12"
        selected = None

    out = {
        "schema": "same_run_candidate_route_v99_12",
        "decision": decision,
        "passing_candidate_count": len(passed),
        "passing_candidates": [r["candidate_uid"] for r in passed],
        "selected_candidate": selected,
        "authorizes_optimizer": False,
        "authorizes_object_movement": False,
        "authorizes_contact_collision_flow": False,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    j = args.out_dir / "same_run_candidate_route_v99_12.json"
    j.write_text(json.dumps(out, indent=2) + "\n")
    md = args.out_dir / "same_run_candidate_route_v99_12.md"
    md.write_text(
        "# v99.12 Candidate Route\n\n"
        f"- Decision: `{decision}`\n"
        f"- Passing candidates: {len(passed)}\n"
        f"- Selected candidate: `{selected}`\n"
        "- Optimizer authorization: `false`\n"
    )
    print(f"[PASS] ROUTE={j}")


if __name__ == "__main__":
    main()
