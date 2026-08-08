#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selector-result", required=True)
    parser.add_argument("--crop-policy", required=True)
    parser.add_argument("--numeric-thresholds", required=True)
    parser.add_argument("--identity-scope", required=True)
    parser.add_argument("--consensus-policy", required=True)
    parser.add_argument("--professor-approved", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    paths = {name: Path(value) for name, value in {
        "selector_result": args.selector_result,
        "crop_policy": args.crop_policy,
        "numeric_thresholds": args.numeric_thresholds,
        "identity_scope": args.identity_scope,
        "consensus_policy": args.consensus_policy,
    }.items()}
    missing = [f"{name}:{path}" for name, path in paths.items() if not path.is_file()]
    if missing:
        print(f"[HOLD] MISSING_INPUTS={missing}")
        return 0

    result = json.loads(paths["selector_result"].read_text())
    selected = result.get("selected_candidate_uid")
    selector_pass = result.get("decision") in {
        "select_one_medoid_anchor",
        "select_single_identity_valid_survivor",
    } and isinstance(selected, str) and selected != ""

    authorized = bool(args.professor_approved and selector_pass)
    packet = {
        "schema": "one_v3_multicrop_execution_authorization_packet",
        "calibration_case": "alapuse02v6n60",
        "target_case": "alapuse02v3n60",
        "frozen_v6_selected_anchor": selected,
        "selector_pass": selector_pass,
        "professor_approved": bool(args.professor_approved),
        "frozen_input_hashes": {name: sha256(path) for name, path in paths.items()},
        "requirements": {
            "identical_15_crop_lattice": True,
            "identical_hamer_source_and_checkpoint": True,
            "identical_handedness_policy": True,
            "identical_metric_reanchor": True,
            "identical_numeric_thresholds": True,
            "identical_identity_schema": True,
            "identical_consensus_and_reject_all_policy": True,
            "blind_application_to_v3": True,
        },
        "authorizes_exactly_one_v3_multicrop_execution": authorized,
        "authorizes_optimizer": False,
        "authorizes_contact_collision_flow": False,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2) + "\n")
    print(f"[PASS] PACKET={out}")
    print(f"[INFO] V3_AUTHORIZED={authorized}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
