from __future__ import annotations

import argparse
from pathlib import Path
import sys

from common import ProbeConfigError, read_json, write_json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preflight", required=True)
    ap.add_argument("--fd", required=True)
    ap.add_argument("--analysis", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    try:
        pre = read_json(args.preflight)
        fd = read_json(args.fd)
        an = read_json(args.analysis)
        rationale = []
        if pre.get("status") != "PASS":
            route = "HOLD_IDENTITY_OR_CONFIGURATION_FAILURE"
            rationale.append("The exact zero-update projection/normalization contract did not pass.")
        elif fd.get("status") != "PASS":
            route = "HOLD_FINITE_DIFFERENCE_NUMERICAL_INSTABILITY"
            rationale.append("Finite-difference columns or zero-state repeatability are unstable.")
        elif an.get("status") != "COMPLETE":
            route = "HOLD_ANALYSIS_INCOMPLETE"
            rationale.append("The span analysis did not complete.")
        else:
            blocks = an.get("blocks", {})
            active = blocks.get("active_articulation", {})
            trans = blocks.get("translation_only", {})
            combined = blocks.get("translation_plus_active", {})
            all_art = blocks.get("all_articulation_upper_bound", {})
            known_trans_rejected = bool(an.get("known_branch_e_translation_rejected", False))
            if known_trans_rejected and trans.get("passes_adequacy"):
                route = "HOLD_PROBE_CONTRADICTS_REGISTERED_BRANCH_E"
                rationale.append("The local linear probe says translation is adequate, but the registered nonlinear Branch E rejected translation. Reconcile inputs/normalization before authorization.")
            elif active.get("passes_adequacy"):
                route = "ROUTE_A_PREREGISTER_BOUNDED_ACTIVE_ARTICULATION_TRIAL"
                rationale.append("The lowest-dimensional active-finger articulation block explains the residual within frozen bounds and stability criteria.")
            elif combined.get("passes_adequacy"):
                route = "ROUTE_B_PREREGISTER_BOUNDED_TRANSLATION_PLUS_ACTIVE_ARTICULATION_TRIAL"
                rationale.append("Active articulation alone is inadequate, while the registered translation-plus-active span is adequate.")
            elif all_art.get("passes_adequacy"):
                route = "ROUTE_C_AUDIT_ALTERNATE_CANDIDATES_FULL_HAND_UPPER_BOUND_ONLY"
                rationale.append("Only the over-parameterized all-articulation sensitivity block is adequate; this does not justify a full-hand optimizer.")
            else:
                route = "ROUTE_C_AUDIT_ALTERNATE_SAME_RUN_HAND_CANDIDATES"
                rationale.append("No authorized local pose family explains enough of the residual within bounds.")

        decision = {
            "route": route,
            "rationale": rationale,
            "authorizes_nonzero_optimization": route.startswith("ROUTE_A_") or route.startswith("ROUTE_B_"),
            "still_unauthorized": [
                "C2 until a separately preregistered trial passes projection and silhouette",
                "contact attraction",
                "collision optimization",
                "F3.4",
                "Gate D",
                "independent lid/base transforms",
                "silent target rewriting",
            ],
        }
        write_json(out / "decision.json", decision)
        lines = [
            "# Gate-C read-only articulation-adequacy decision",
            "",
            f"**Route:** `{route}`",
            "",
            "## Rationale",
            "",
        ] + [f"- {x}" for x in rationale] + [
            "",
            "## Authorization boundary",
            "",
            f"Nonzero placement trial authorized by this route: **{'yes, but only after a separate preregistration' if decision['authorizes_nonzero_optimization'] else 'no'}**.",
            "",
            "The read-only probe itself never authorizes C2, contact/collision, F3.4, or Gate D.",
        ]
        (out / "decision.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[{route}]")
        return 0
    except ProbeConfigError as exc:
        write_json(out / "decision.json", {"route": "CONFIG_ERROR", "message": str(exc)})
        print(f"[CONFIG_ERROR] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        write_json(out / "decision.json", {"route": "DECISION_ERROR", "message": repr(exc)})
        print(f"[DECISION_ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
