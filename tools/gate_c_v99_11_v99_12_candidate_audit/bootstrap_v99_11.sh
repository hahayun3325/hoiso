#!/usr/bin/env bash
set -euo pipefail

: "${METHOD_ROOT:?Set METHOD_ROOT to the case Gate-C method root}"

V99_11_ROOT="${V99_11_ROOT:-$METHOD_ROOT/alternate_same_run_hamer_candidate_audit_v99_11}"
mkdir -p \
  "$V99_11_ROOT/config" \
  "$V99_11_ROOT/evidence" \
  "$V99_11_ROOT/zero_states" \
  "$V99_11_ROOT/reports" \
  "$V99_11_ROOT/visuals" \
  "$V99_11_ROOT/hashes" \
  "$V99_11_ROOT/notes"

cat > "$V99_11_ROOT/config/scope_v99_11.json" <<'JSON'
{
  "schema": "alternate_same_run_hamer_candidate_audit_scope_v99_11",
  "allowed": [
    "inventory_same_run_candidates",
    "resolve_historical_selected_index",
    "source_faithful_zero_projection",
    "independent_upper_hand_numeric_gate",
    "indexed_vlm_review_after_numeric_gate"
  ],
  "closed": [
    "widen_rejected_family",
    "prepare_v100_for_rejected_family",
    "reuse_v99_9_solution",
    "nonzero_pose",
    "optimizer",
    "object_movement",
    "contact",
    "collision",
    "flow",
    "C2",
    "F3_4",
    "Gate_D"
  ],
  "authorizes_optimizer": false
}
JSON

if [[ ! -e "$V99_11_ROOT/config/candidate_manifest.csv" ]]; then
  cat > "$V99_11_ROOT/config/candidate_manifest.csv" <<'CSV'
candidate_uid,batch_file,batch_index,crop_id,provenance_pass,handedness_pass,crop_raster_pass,physical_upper_hand_pass,positive_depth_pass,projected_kps_path,candidate_depth_path,candidate_mask_path,notes
CSV
fi

if [[ ! -e "$V99_11_ROOT/config/candidate_gate_policy.json" ]]; then
  cat > "$V99_11_ROOT/config/candidate_gate_policy.json" <<'JSON'
{
  "schema": "candidate_zero_state_gate_policy_v99_12",
  "threshold_source": "MUST_BE_CALIBRATED_AND_FROZEN_ON_V6_BEFORE_V3_REVIEW",
  "max_normalized_rmse": null,
  "max_normalized_p95": null,
  "require_silhouette": false,
  "min_silhouette_iou": null,
  "require_positive_depth": true,
  "require_provenance": true,
  "require_handedness": true,
  "require_crop_raster": true,
  "require_physical_upper_hand": true,
  "authorizes_optimizer": false
}
JSON
fi

printf '[PASS] V99_11_ROOT=%s\n' "$V99_11_ROOT"
printf '[HOLD] Fill source lineage, independent target, and v6-calibrated thresholds before candidate routing.\n'
