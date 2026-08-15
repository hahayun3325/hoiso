#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text())
    policy = json.loads(Path(args.policy).read_text())
    thresholds = policy["routing_thresholds"]
    ratios = report["weighted_residual_ratios"]
    morphology = report["orthogonal_residual_morphology"]
    groups = report["group_energy_fraction"]["unbounded_span_floor"]

    span_floor = ratios["unbounded_span_floor"]
    gap = ratios["bounded_minus_unbounded_gap"]
    tangential = morphology["tangential_only_r2"]
    radial = morphology["radial_only_r2"]
    inactive = groups.get("thumb", 0.0) + groups.get("ring", 0.0) + groups.get("pinky", 0.0)
    broad_count = sum(1 for name, value in groups.items() if name != "wrist" and value >= thresholds["minimum_chain_energy_fraction"])

    if span_floor is not None and gap is not None and span_floor <= thresholds["bound_limited_span_floor_ratio_max"] and gap >= thresholds["bound_limited_constraint_gap_ratio_min"]:
        decision = "review_bound_adequacy_or_nonlinear_curvature_before_adding_mode_v88"
        rationale = "The existing 17-mode span explains the target well when unbounded, while the registered bounded solution leaves a materially larger residual. This is not evidence for an arbitrary ratio change; it requires a separate physical-bound or trust-region hypothesis."
    elif tangential >= thresholds["root_rotation_tangential_r2_min"] and broad_count >= thresholds["minimum_broad_chain_count"]:
        decision = "preregister_translation_root_rotation_active_articulation_v89"
        rationale = "The residual outside the existing span has a broad tangential pattern consistent with testing a source-bound root-rotation family."
    elif radial >= thresholds["hand_scale_radial_r2_min"] and broad_count >= thresholds["minimum_broad_chain_count"]:
        decision = "preregister_translation_hand_scale_active_articulation_v89"
        rationale = "The residual outside the existing span has a broad radial pattern consistent with a scale diagnostic."
    elif inactive >= thresholds["inactive_chain_energy_fraction_min"]:
        decision = "preregister_source_proven_broader_articulation_v89"
        rationale = "Most of the residual outside the existing span is concentrated on inactive finger chains."
    else:
        decision = "audit_alternate_same_run_hamer_candidates_v89"
        rationale = "No single coherent root-rotation, scale, or inactive-chain pattern is strong enough to justify adding a new continuous mode."

    output = {
        "schema": "v88_next_family_route",
        "decision": decision,
        "rationale": rationale,
        "diagnostics": {
            "unbounded_span_floor_ratio": span_floor,
            "bounded_minus_unbounded_gap_ratio": gap,
            "tangential_r2": tangential,
            "radial_r2": radial,
            "inactive_chain_energy_fraction": inactive,
            "broad_chain_count": broad_count,
        },
        "root_rotation_policy_if_selected": policy["root_rotation_preregistration"],
        "authorizes_new_derivative_policy": True,
        "authorizes_derivative_collection": False,
        "authorizes_optimizer": False,
        "authorizes_nonzero_mesh": False,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "next_family_route_v88.json"
    md_path = out_dir / "next_family_route_v88.md"
    json_path.write_text(json.dumps(output, indent=2) + "\n")
    md_path.write_text(
        "# v88 next-family route\n\n"
        f"**Decision:** `{decision}`\n\n"
        f"{rationale}\n\n"
        "This route authorizes policy drafting only. It does not authorize derivative collection, optimization, or a nonzero hand mesh.\n"
    )
    print(f"[PASS] V88_ROUTE={json_path}")
    print(f"[HOLD] V88_AUTHORIZES_OPTIMIZER={output['authorizes_optimizer']}")


if __name__ == "__main__":
    main()
