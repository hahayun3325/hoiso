#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

ART_READY = {
    "ROUTE_A_PREREGISTER_BOUNDED_ACTIVE_ARTICULATION_TRIAL",
    "ROUTE_B_PREREGISTER_BOUNDED_TRANSLATION_PLUS_ACTIVE_ARTICULATION_TRIAL",
}
ART_CANDIDATE = {
    "ROUTE_C_AUDIT_ALTERNATE_SAME_RUN_HAND_CANDIDATES",
    "ROUTE_C_AUDIT_ALTERNATE_CANDIDATES_FULL_HAND_UPPER_BOUND_ONLY",
}

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root-report", required=True)
    p.add_argument("--articulation-decision", required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()
    root = json.loads(Path(args.root_report).read_text(encoding="utf-8"))
    art = json.loads(Path(args.articulation_decision).read_text(encoding="utf-8"))
    rc, ar = root.get("classification"), art.get("route")
    rationale = []
    if root.get("status") != "COMPLETE":
        route = "HOLD_ROOT_AUDIT_INCOMPLETE"
        rationale.append("The object-root audit did not complete.")
    elif ar is None or ar.startswith("HOLD_") or ar in {"CONFIG_ERROR", "DECISION_ERROR"}:
        route = "HOLD_ARTICULATION_PROBE"
        rationale.append("The read-only articulation probe is not interpretable or is numerically inconsistent.")
    elif rc == "ROOT_IDENTITY_CONFIRMED" and ar in ART_READY:
        route = "V57_READY_TO_PREREGISTER_ONE_BOUNDED_HAND_TRIAL"
        rationale.append("The part-aware object root is preserved and an authorized local hand family spans the residual.")
    elif rc == "ROOT_IDENTITY_CONFIRMED" and ar in ART_CANDIDATE:
        route = "V57_AUDIT_ALTERNATE_SAME_RUN_HAND_CANDIDATES"
        rationale.append("The object root is not the blocker and the local hand family is inadequate.")
    elif rc == "SAME_GEOMETRY_NONIDENTITY_ROOT":
        route = "V57_REPAIR_OR_REPRODUCE_ONE_WHOLE_OBJECT_ROOT_FIRST"
        rationale.append("One similarity explains the object difference, but its cause must be classified before any hand trial.")
        if ar in ART_READY:
            rationale.append("The hand probe may remain useful, but nonzero work stays blocked until the object-root contract is repaired and zero overlays are rerun.")
    elif rc == "GEOMETRY_OR_CANDIDATE_CHANGED":
        route = "V57_BIND_ACCEPTED_OBJECT_CANDIDATE_AND_ESTIMATE_ITS_METRIC_ROOT"
        rationale.append("The accepted object is not a root-only re-expression of the earlier mesh; the prior hand-object transform is obsolete.")
    else:
        route = "HOLD_RECOVER_OBJECT_VERTEX_LINEAGE"
        rationale.append("A near-identity geometric fit without source lineage is insufficient to prove root preservation.")
    decision = {
        "schema": "v57_dual_read_only_gate_c_route_v1",
        "object_root_classification": rc,
        "articulation_route": ar,
        "route": route,
        "rationale": rationale,
        "authorizes_optimizer_launch": False,
        "next_action_is_preregistration_only": route == "V57_READY_TO_PREREGISTER_ONE_BOUNDED_HAND_TRIAL",
        "still_closed": ["contact_attraction", "collision", "short_flow", "C2", "F3.4", "Gate_D", "independent_lid_base_scale"],
    }
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "decision.json").write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    md = ["# v57 dual read-only Gate-C decision", "", f"**Route:** `{route}`", "", "## Rationale", ""] + [f"- {x}" for x in rationale] + ["", "No optimizer launch is authorized by this report."]
    (out / "decision.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(decision, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
