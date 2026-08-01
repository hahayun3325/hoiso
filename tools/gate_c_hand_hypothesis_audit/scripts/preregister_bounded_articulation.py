#!/usr/bin/env python3
"""Write a non-authorizing preregistration for a bounded MANO refinement.

This does not run an optimizer. It binds input hashes, records the selected
source-verified hand candidate, and freezes a staged variable/loss policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(f"argument_error: {message}")


def bind(path: Path | None) -> dict:
    if path is None:
        return {"missing": True}
    path = path.expanduser().resolve()
    if not path.is_file():
        return {"path": str(path), "missing": True}
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"path": str(path), "sha256": h, "size_bytes": path.stat().st_size}


def main() -> int:
    parser = SafeArgumentParser()
    parser.add_argument("--audit-summary", required=True, type=Path)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--branch-e-result", required=True, type=Path)
    parser.add_argument("--target-kps", required=True, type=Path)
    parser.add_argument("--mano-params", type=Path)
    parser.add_argument("--hand-mask", type=Path)
    parser.add_argument("--object-assembly", type=Path)
    parser.add_argument("--lid-mesh", type=Path)
    parser.add_argument("--base-mesh", type=Path)
    parser.add_argument("--active-fingers", default="thumb,index,middle")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    audit = json.loads(args.audit_summary.read_text())
    candidates = {c.get("candidate_id"): c for c in audit.get("candidates", [])}
    candidate = candidates.get(args.candidate_id)
    if candidate is None:
        print(f"[HOLD] CANDIDATE_NOT_IN_AUDIT={args.candidate_id}")
        return 0
    if candidate.get("metadata_contract_pass") is not True:
        print("[HOLD] SOURCE_IDENTITY_COORDINATE_CONTRACT_NOT_VERIFIED")
        return 0
    if candidate.get("route") == "HOLD_REFLECTED_ONLY":
        print("[HOLD] REFLECTED_ONLY_CANDIDATE_NOT_ELIGIBLE")
        return 0
    if candidate.get("route") not in {
        "PASS_CORRESPONDENCE_CANDIDATE",
        "FAIL_GLOBAL_CORRESPONDENCE",
    }:
        print(f"[HOLD] CANDIDATE_ROUTE_NOT_ELIGIBLE={candidate.get('route')}")
        return 0

    active_fingers = [x.strip() for x in args.active_fingers.split(",") if x.strip()]
    allowed_fingers = {"thumb", "index", "middle", "ring", "pinky"}
    if not active_fingers or any(x not in allowed_fingers for x in active_fingers):
        print(f"[HOLD] INVALID_ACTIVE_FINGERS={active_fingers}")
        return 0

    record = {
        "schema_version": "gate_c_bounded_mano_articulation_preregistration_v1",
        "case_id": "alapuse02v3n60",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PREPARED_NOT_AUTHORIZED",
        "scientific_question": (
            "Can a source-verified upper-hand hypothesis be reconciled with the frozen "
            "target through a bounded root plus selected-finger MANO update without "
            "scale change, reflection, object movement, or contact-loss shortcut?"
        ),
        "selected_candidate": {
            "candidate_id": args.candidate_id,
            "audit_route": candidate.get("route"),
            "source_identity_status": candidate.get("source_identity_status"),
            "handedness": candidate.get("handedness"),
            "audit_summary": bind(args.audit_summary),
        },
        "bound_inputs": {
            "branch_e_result": bind(args.branch_e_result),
            "target_keypoints": bind(args.target_kps),
            "mano_parameters": bind(args.mano_params),
            "hand_mask": bind(args.hand_mask),
            "object_assembly": bind(args.object_assembly),
            "screen_lid": bind(args.lid_mesh),
            "keyboard_base": bind(args.base_mesh),
        },
        "variables": {
            "hand_scale": {"trainable": False},
            "hand_shape_beta": {"trainable": False},
            "object_geometry": {"trainable": False},
            "object_global_similarity": {"trainable": False},
            "lid_base_relative_transform": {"trainable": False},
            "hand_root_translation": {
                "trainable": True,
                "bound_policy": "not_larger_than_registered_branch_e_radius",
            },
            "hand_root_rotation": {
                "trainable": True,
                "parameterization": "axis_angle",
                "max_delta_deg_per_axis": 10.0,
            },
            "mano_active_finger_pose": {
                "trainable": True,
                "active_fingers": active_fingers,
                "max_delta_deg_per_axis": 20.0,
            },
            "mano_nonactive_finger_pose": {"trainable": False},
            "wrist_articulation": {
                "trainable": False,
                "note": "enable only in a separate ablation after the selected-finger branch",
            },
        },
        "stages": [
            {
                "stage": "A_keypoint_only",
                "losses": {
                    "robust_2d_keypoint_reprojection": 1.0,
                    "root_transform_prior": 0.1,
                    "mano_pose_delta_prior": 1.0,
                    "joint_limit_penalty": 1.0,
                    "silhouette": 0.0,
                    "contact": 0.0,
                    "collision": 0.0,
                },
                "steps": 150,
                "optimizer": "Adam",
                "learning_rate": {
                    "root_translation": 1e-3,
                    "root_rotation": 5e-4,
                    "mano_pose": 5e-4,
                },
            },
            {
                "stage": "B_silhouette_anchor",
                "activation": "only_if_stage_A_meets_registered_2d_thresholds",
                "losses": {
                    "robust_2d_keypoint_reprojection": 1.0,
                    "hand_silhouette": 0.25,
                    "root_transform_prior": 0.1,
                    "mano_pose_delta_prior": 1.0,
                    "joint_limit_penalty": 1.0,
                    "contact": 0.0,
                    "collision": 0.0,
                },
                "steps": 100,
                "optimizer": "Adam_then_optional_LBFGS",
            },
            {
                "stage": "C_weak_part_preference_diagnostic",
                "activation": (
                    "only_if_stage_B_passes; diagnostic only; active fingertips may be weakly "
                    "encouraged toward screen_lid, but Gate-D contact/collision remain off"
                ),
                "losses": {
                    "robust_2d_keypoint_reprojection": 1.0,
                    "hand_silhouette": 0.25,
                    "screen_lid_preference": 0.05,
                    "contact": 0.0,
                    "collision": 0.0,
                },
                "steps": 50,
            },
        ],
        "acceptance": {
            "proper_fit_required": True,
            "reflected_fit_cannot_authorize": True,
            "normalized_rmse_max": 0.50,
            "normalized_p95_max": 0.75,
            "pairwise_structure_nonregression": True,
            "silhouette_nonregression": True,
            "translation_trust_fraction_lt": 0.98,
            "all_parameter_bounds_respected": True,
            "no_nan_or_invalid_depth": True,
            "object_mesh_hash_unchanged": True,
            "lid_base_relative_transform_unchanged": True,
        },
        "stopping_rule": {
            "one_selected_source_verified_candidate": True,
            "one_registered_dof_policy": True,
            "no_bound_expansion_after_result": True,
            "failure_route": "freeze_or_open_separate_object_root_ASR_only_if_hand_2d_fit_passes",
        },
        "authorizations": {
            "run_optimizer": False,
            "run_c2": False,
            "run_f34": False,
            "run_gate_d": False,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        print(f"[HOLD] PREREGISTRATION_ALREADY_EXISTS={args.out}")
        return 0
    args.out.write_text(json.dumps(record, indent=2) + "\n")
    print(f"[PASS] PREREGISTRATION_WRITTEN={args.out}")
    print("[INFO] STATUS=PREPARED_NOT_AUTHORIZED")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as error:
        print(f"[HOLD] PREREGISTRATION_NOT_WRITTEN={type(error).__name__}: {error}")
        code = 0
    raise SystemExit(code)
