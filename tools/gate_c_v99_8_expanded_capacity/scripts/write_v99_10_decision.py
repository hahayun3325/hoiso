#!/usr/bin/env python3
"""Write a non-authorizing scientific route from the v99.9 capacity report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_json = args.out_dir / "expanded_capacity_scientific_decision_v99_10.json"
    out_md = args.out_dir / "expanded_capacity_scientific_decision_v99_10.md"
    if not args.report.is_file():
        data = {"schema": "expanded_capacity_scientific_decision_v99_10", "decision": "hold_missing_v99_9_report", "authorizes_optimizer_policy_preparation": False, "authorizes_optimizer_execution": False}
    else:
        report = json.loads(args.report.read_text())
        raw = report.get("decision")
        failed = report.get("failed_checks", [])
        metrics = report.get("metrics", {})
        if raw == "pass_expanded_bounded_capacity_v99_9":
            decision = "prepare_v100_bounded_gate_c_optimizer_policy_only"
            note = "The selected 22-variable family passes read-only bounded capacity. Prepare and review an optimizer policy; do not execute it yet."
            prep = True
        elif raw == "reject_expanded_bounded_capacity_v99_9":
            boundary = any("bound_fraction" in x or "saturated" in x for x in failed)
            decision = "audit_alternate_same_run_hamer_candidates_or_close_gate_c" if boundary else "hold_selected_scale_family_target_capacity_failed"
            note = "The selected family did not earn optimizer preparation. Preserve the rejection and follow the stated fail-closed route."
            prep = False
        else:
            decision = "hold_repair_v99_9_inputs_or_solver_only"
            note = "The capacity run did not produce a scientific pass/fail. Repair inputs or solver without changing the family or thresholds."
            prep = False
        data = {
            "schema": "expanded_capacity_scientific_decision_v99_10",
            "decision": decision,
            "source_report_decision": raw,
            "failed_checks": failed,
            "summary_metrics": {
                key: metrics.get(key) for key in (
                    "weighted_residual_energy_coverage",
                    "bounded_residual_norm_ratio",
                    "predicted_rmse_reduction_fraction",
                    "translation_bound_fraction",
                    "scale_bound_fraction",
                    "maximum_articulation_bound_fraction",
                    "saturated_articulation_fraction",
                )
            },
            "note": note,
            "authorizes_optimizer_policy_preparation": prep,
            "authorizes_optimizer_execution": False,
            "authorizes_C2": False,
            "authorizes_contact_collision_or_flow": False,
        }
    out_json.write_text(json.dumps(data, indent=2) + "\n")
    lines = [
        "# v99.10 Expanded-Capacity Scientific Decision",
        "",
        f"**Decision:** `{data['decision']}`",
        "",
        data.get("note", ""),
        "",
        "```text",
        f"optimizer policy preparation: {data.get('authorizes_optimizer_policy_preparation')}",
        f"optimizer execution:          {data.get('authorizes_optimizer_execution')}",
        f"C2:                           {data.get('authorizes_C2')}",
        "```",
        "",
    ]
    out_md.write_text("\n".join(lines))
    print(f"[INFO] V99_10_DECISION={data['decision']} JSON={out_json} MD={out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
