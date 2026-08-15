#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    contract = json.loads(Path(a.contract).read_text())
    policy = json.loads(Path(a.policy).read_text())
    out_dir = Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    if contract.get("status") != "PASS":
        raise SystemExit("[HOLD] compiled D0 contract is not PASS")
    active = contract.get("active_hand_parameter_names", [])
    contacts = contract.get("compiled_contacts", [])
    forbidden = contract.get("compiled_forbidden_regions", [])
    hp = policy["hand_phase"]; jp = policy["joint_phase"]
    hand = {
      "schema": "hoiso_hand_phase_objective_v1",
      "purpose": "D0-guided local hand refinement with Gate-A object frozen",
      "trainable": {"selected_hand_parameters": active},
      "frozen": ["Gate-A object geometry", "object root", "object articulation", "hand global scale", "hand shape", "hand global R,t", "unselected hand parameters"],
      "soft_objective_terms": {
        "selected_contact": contacts,
        "pose_regularization": {"weight": hp["base_weights"]["pose_regularization"]},
        "ordered_keypoint_reprojection": {"weight": hp["base_weights"]["keypoint"]}
      },
      "barrier_or_monitor_terms": {
        "hand_mask": hp["base_weights"]["mask"],
        "valid_hand_depth": hp["base_weights"]["depth"],
        "valid_dense_z_order": hp["base_weights"]["z_order"],
        "forbidden_regions": forbidden,
        "penetration": hp["base_weights"]["penetration"]
      },
      "hard_acceptance_gates": ["keypoint", "mask_precision_and_spill", "valid_depth", "valid_dense_z_order", "forbidden_contact_empty", "penetration", "provenance_and_topology"],
      "checkpoints": hp["checkpoints"],
      "extension_policy": {"step_10": hp["max_first_extension"], "step_20": hp["max_second_extension"], "condition": "all hard gates pass and target metrics improve without bound pressure"},
      "select": "earliest fully passing checkpoint",
      "authorizes_execution": False
    }
    allowed_parts = sorted(set(c["object_part"] for c in contacts if c["attraction_policy"] != "diagnostic_only"))
    allow_hinge = bool(jp["allow_hinge_residual"] and "screen_lid" in allowed_parts)
    joint = {
      "schema": "hoiso_joint_phase_objective_v1",
      "purpose": "D0-guided bounded relative refinement after accepted hand and object states",
      "trainable": {
        "selected_hand_parameters": active,
        "object_root_translation": bool(jp["allow_object_root_translation"]),
        "object_root_rotation": bool(jp["allow_object_root_rotation"]),
        "bounded_hinge_residual": allow_hinge
      },
      "frozen": ["object topology", "part membership", "base geometry", "object scale" if not jp["allow_object_scale"] else "", "hand shape", "unselected hand parameters", "unbounded flow geometry"],
      "soft_objective_terms": {
        "selected_contact": contacts,
        "hand_image_consistency": {"weight": jp["base_weights"]["hand_image"]},
        "object_image_consistency": {"weight": jp["base_weights"]["object_image"]},
        "hand_trust_region": {"weight": jp["base_weights"]["hand_trust"]},
        "object_trust_region": {"weight": jp["base_weights"]["object_trust"]},
        "hinge_trust": {"weight": jp["base_weights"]["hinge_trust"], "active": allow_hinge}
      },
      "barrier_or_monitor_terms": {
        "valid_dense_z_order": jp["base_weights"]["z_order"],
        "forbidden_regions": forbidden,
        "penetration": jp["base_weights"]["penetration"],
        "Gate-A_non_regression": True
      },
      "hard_acceptance_gates": ["hand_keypoint_mask_depth", "object_silhouette_depth_normal", "selected_contact_gap", "forbidden_contact_empty", "penetration", "z_order", "part_state", "topology_and_scale"],
      "checkpoints": jp["checkpoints"],
      "max_extension": jp["max_extension"],
      "select": "earliest fully passing checkpoint",
      "authorizes_execution": False
    }
    joint["frozen"] = [x for x in joint["frozen"] if x]
    (out_dir/"hand_phase_objective.json").write_text(json.dumps(hand,indent=2)+"\n")
    (out_dir/"joint_phase_objective.json").write_text(json.dumps(joint,indent=2)+"\n")
    print(f"[PASS] wrote {out_dir/'hand_phase_objective.json'}")
    print(f"[PASS] wrote {out_dir/'joint_phase_objective.json'}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
