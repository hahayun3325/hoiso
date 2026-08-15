#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from common import read_json, write_json


def parser() -> Tuple[argparse.Namespace, list[str]]:
    p = argparse.ArgumentParser(description="Route Gate C after source-identity reports; never launches optimization.")
    p.add_argument("--h0", default="")
    p.add_argument("--h2", default="")
    p.add_argument("--h3", default="")
    p.add_argument("--h4", default="")
    p.add_argument("--source-mapping", default="")
    p.add_argument("--producer-unresolved", action="store_true")
    p.add_argument("--out-dir", default="")
    return p.parse_known_args()


def optional_report(path: str) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(p)
    return read_json(p)


def direct_identity_ok(report: Optional[Dict[str, Any]]) -> bool:
    if report is None:
        return False
    direct = report.get("direct", {})
    return bool(direct.get("shape_match")) and direct.get("max_abs_coordinate_error", float("inf")) < float("inf")


def main() -> int:
    args, unknown = parser()
    if unknown:
        print(f"[HOLD] Unknown arguments: {unknown}", file=sys.stderr)
        return 1
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else Path.cwd() / "lineage_decision"
    out_dir.mkdir(parents=True, exist_ok=True)

    decision: Dict[str, Any] = {
        "status": "HOLD_DECISION_NOT_COMPLETED",
        "authorizes_mapping": False,
        "authorizes_corrected_target": False,
        "authorizes_candidate_scoring": False,
        "authorizes_mesh_movement": False,
        "authorizes_C2": False,
        "authorizes_F3_4": False,
        "authorizes_Gate_D": False,
    }

    try:
        if args.producer_unresolved:
            route = "ROUTE_U_CONTAINED_LINEAGE_FAILURE"
            reason = "The exact active producer or immutable run artifacts could not be recovered."
        else:
            h0 = optional_report(args.h0)
            h2 = optional_report(args.h2)
            h3 = optional_report(args.h3)
            h4 = optional_report(args.h4)

            mapping = optional_report(args.source_mapping)
            mapping_proven = bool(mapping and mapping.get("source_proven") is True)

            if h0 is None:
                route = "ROUTE_U_CONTAINED_LINEAGE_FAILURE"
                reason = "No H0 report was supplied; the source contract remains unresolved."
            elif h0.get("H0", {}).get("pass") is not True:
                route = "ROUTE_J_ACTIVE_SOURCE_OR_STATE_MISMATCH"
                reason = "Raw saved HaMeR vertices do not reproduce raw saved pred_keypoints_3d under the supplied active contract."
            elif h0.get("H1", {}).get("internal_handedness_pass") is not True:
                route = "ROUTE_J_CHIRALITY_OR_GUIDANCE_STAGE_MISMATCH"
                reason = "Raw identity passes, but the handedness-adjusted identity fails."
            elif h0.get("H1", {}).get("guidance_pass") is False:
                route = "ROUTE_J_GUIDANCE_FILE_OR_CANDIDATE_MISMATCH"
                reason = "The selected guidance 3D keypoints do not match the handedness-adjusted source joints."
            elif h2 is None:
                route = "HOLD_BEFORE_H2_PROJECTION_IDENTITY"
                reason = "H0/H1 pass, but source-faithful 2D projection identity has not been shown."
            elif h2.get("status") != "PASS_DIAGNOSTIC_COMPARISON_WRITTEN":
                route = "HOLD_H2_REPORT_INVALID"
                reason = "The H2 comparison report is incomplete or invalid."
            elif h3 is None:
                route = "HOLD_BEFORE_H3_SHARED_FRAME_IDENTITY"
                reason = "H2 exists, but the exact C1/shared-frame transform identity has not been shown."
            elif h4 is None:
                route = "HOLD_BEFORE_H4_LIVE_HELPER_IDENTITY"
                reason = "H3 exists, but the exact zero-update live-helper identity has not been shown."
            else:
                route = "READY_FOR_SOURCE_VERIFIED_CANDIDATE_AUDIT"
                reason = "The identity ladder is present through H4. Candidate identity may now be audited, but placement is still not authorized."
                decision["authorizes_candidate_scoring"] = True

            if mapping_proven:
                decision["source_proven_mapping_present"] = True
                decision["mapping_note"] = (
                    "A source-proven mapping file is present, but mapping remains non-authorized until the H0-H4 direct identity checks pass under that mapping."
                )

        decision.update({"status": route, "reason": reason})
        write_json(out_dir / "decision.json", decision)

        md = [
            "# Gate-C keypoint-lineage decision",
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
            "authorizes_C2",
            "authorizes_F3_4",
            "authorizes_Gate_D",
        ]:
            md.append(f"- `{key}`: `{str(decision[key]).lower()}`")
        md.extend(
            [
                "",
                "The router never authorizes a reflected hand or a numerically guessed permutation.",
            ]
        )
        (out_dir / "decision.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        print(f"[{ 'PASS' if route.startswith('READY') else 'HOLD' }] {route}")
        print(out_dir / "decision.json")
        return 0 if route.startswith("READY") else 1
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
