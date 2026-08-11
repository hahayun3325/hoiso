#!/usr/bin/env bash
set -euo pipefail

main() {

# HOISO-Flow deadline branch: preparation-only bootstrap.
# This script DOES NOT execute object-only optimization, joint flow, Gate D,
# or any GPU workload. It prepares a versioned source copy, hashes the frozen
# inputs, writes fail-closed policy templates, and stops for source review.

PROJECT_ROOT="${PROJECT_ROOT:-/home/fredcui/Projects/FollowMyHold}"
DATA_ROOT="${DATA_ROOT:-/home/fredcui/foho_phase0}"
CASE_ROOT="${CASE_ROOT:-$DATA_ROOT/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2}"
ACTIVE_PYTHON="${ACTIVE_PYTHON:-/home/fredcui/anaconda3/envs/foho/bin/python}"

PIPE_PARENT="${PIPE_PARENT:-$PROJECT_ROOT/third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines_v99_11_7_13_3_12_3_3.py}"
PIPE_TARGET="${PIPE_TARGET:-$PROJECT_ROOT/third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines_v99_11_7_13_3_13.py}"
CPU_7DOF_SOURCE="${CPU_7DOF_SOURCE:-$PROJECT_ROOT/tools/gate_c_v99_11_hand_anchor/run_v3_CPU_7DoF_global_hand_alignment_v99_11_7_13_3_6.py}"
GATE_D_PARENT="${GATE_D_PARENT:-$PROJECT_ROOT/scripts/phase2/gate_d0_fit_v1_articulated_fit.py}"
HAND_ROOT="${HAND_ROOT:-$CASE_ROOT/gate_c_hand_anchor}"
HANDOFF_ROOT="${HANDOFF_ROOT:-$HAND_ROOT/frozen_s100_up_pipeline_handoff_v99_11_7_13_3_13}"

mkdir -p \
  "$HANDOFF_ROOT/config" \
  "$HANDOFF_ROOT/evidence" \
  "$HANDOFF_ROOT/reports" \
  "$HANDOFF_ROOT/hashes" \
  "$HANDOFF_ROOT/launch" \
  "$HANDOFF_ROOT/checkpoints"

require_file() {
  local path="$1"
  if [[ -s "$path" ]]; then
    printf '[PASS] REQUIRED_FILE=%s\n' "$path"
  else
    printf '[HOLD] REQUIRED_FILE_MISSING=%s\n' "$path" >&2
    return 1
  fi
}

require_file "$PIPE_PARENT"
require_file "$CPU_7DOF_SOURCE"
require_file "$GATE_D_PARENT"

mapfile -t seven_dof_results < <(
  find "$HAND_ROOT" -type f \
    -name 'CPU_7DoF_global_hand_result_s100_up_v99_11_7_9_21_7_13_3_8_2.npz' \
    -print | sort
)
mapfile -t fast_routes < <(
  find "$HAND_ROOT" -type f \
    -name 'official_update_sink_and_4090_route_v99_11_7_9_21_7_13_3_12_3_3.json' \
    -print | sort
)
mapfile -t handoff_auths < <(
  find "$HAND_ROOT" -type f \
    -name 'combined_update_sink_and_anchor_handoff_source_authorization_v99_11_7_9_21_7_13_3_12_3_3.json' \
    -print | sort
)

[[ ${#seven_dof_results[@]} -eq 1 ]] || {
  echo "[HOLD] SEVEN_DOF_RESULT_MATCHES=${#seven_dof_results[@]}" >&2
  return 0
}
[[ ${#fast_routes[@]} -eq 1 ]] || {
  echo "[HOLD] FAST_ROUTE_MATCHES=${#fast_routes[@]}" >&2
  return 0
}
[[ ${#handoff_auths[@]} -eq 1 ]] || {
  echo "[HOLD] HANDOFF_POLICY_MATCHES=${#handoff_auths[@]}" >&2
  return 0
}

SEVEN_DOF_RESULT="${seven_dof_results[0]}"
FAST_ROUTE="${fast_routes[0]}"
HANDOFF_POLICY="${handoff_auths[0]}"

printf '[PASS] SEVEN_DOF_RESULT=%s\n' "$SEVEN_DOF_RESULT"
printf '[PASS] FAST_ROUTE=%s\n' "$FAST_ROUTE"
printf '[PASS] HANDOFF_POLICY=%s\n' "$HANDOFF_POLICY"

if [[ -e "$PIPE_TARGET" ]]; then
  echo "[INFO] VERSIONED_PIPELINE_ALREADY_EXISTS=$PIPE_TARGET"
else
  cp -n "$PIPE_PARENT" "$PIPE_TARGET"
  echo "[PASS] VERSIONED_PIPELINE_COPY=$PIPE_TARGET"
fi

"$ACTIVE_PYTHON" -m py_compile "$PIPE_TARGET"

rg -n -C 3 \
  'get_guidance_params|phase=1|phase=1\.5|phase=2|noise_pred_obj|scheduler\.step|scale_hand|translation_hand|rotation_hand' \
  "$PIPE_PARENT" \
  > "$HANDOFF_ROOT/evidence/followmyhold_parent_stage_trace.txt"

rg -n -C 3 \
  'external|anchor|scale_hand|translation_hand|rotation_hand|get_guidance_params|noise_pred_obj|scheduler\.step' \
  "$PIPE_TARGET" \
  > "$HANDOFF_ROOT/evidence/versioned_pipeline_source_trace.txt" || true

sha256sum \
  "$PIPE_PARENT" \
  "$PIPE_TARGET" \
  "$SEVEN_DOF_RESULT" \
  "$CPU_7DOF_SOURCE" \
  "$GATE_D_PARENT" \
  "$FAST_ROUTE" \
  "$HANDOFF_POLICY" \
  > "$HANDOFF_ROOT/hashes/source_and_anchor_inputs.sha256"

cat > "$HANDOFF_ROOT/config/external_anchor_handoff_scope.json" <<JSON
{
  "schema": "external_anchor_handoff_scope_v99_11_7_13_3_13",
  "case_id": "alapuse02v3n60",
  "candidate_uid": "s100_up",
  "anchor_result": "$SEVEN_DOF_RESULT",
  "pipeline_parent": "$PIPE_PARENT",
  "pipeline_target": "$PIPE_TARGET",
  "default_pipeline_behavior_unchanged": true,
  "external_anchor_is_opt_in": true,
  "required_vertex_count": 778,
  "phase_behavior": {
    "hand_only_phase": "bypass_when_external_anchor_active",
    "object_only_phase": "hand_exactly_frozen",
    "joint_phase": "global_hand_delta_under_tight_trust_region"
  },
  "closed": [
    "local_mano_articulation",
    "new_hand_candidate_search",
    "new_object_reconstruction",
    "contact_force_before_joint_review",
    "gate_d_before_joint_review",
    "optimizer_execution"
  ],
  "authorizes_source_edit": true,
  "authorizes_gpu_execution": false
}
JSON

cat > "$HANDOFF_ROOT/config/launch_contract.template.json" <<'JSON'
{
  "schema": "hoiso_v3_fast_track_launch_contract_v1",
  "status": "HOLD_UNTIL_ALL_NULLS_ARE_FILLED_AND_REVIEWED",
  "case_id": "alapuse02v3n60",
  "deadline_branch": true,
  "generalization_claim": false,
  "frozen_inputs": {
    "s100_up_anchor_npz": null,
    "part_aware_object_mesh": null,
    "object_latent_or_noise_state": null,
    "input_rgb": null,
    "hand_mask": null,
    "object_mask": null,
    "gate_b_contact_json": null,
    "h2m_transform": null,
    "hb_transform": null,
    "camera": null,
    "versioned_pipeline": null
  },
  "object_only": {
    "exact_existing_entrypoint": null,
    "step_count": null,
    "learning_rates": null,
    "hand_frozen": true
  },
  "joint_flow": {
    "exact_existing_entrypoint": null,
    "step_count": null,
    "learning_rates": null,
    "hand_translation_radius_palm_widths": 0.05,
    "hand_root_rotation_radius_degrees": 5.0,
    "hand_relative_scale_lower": 0.98,
    "hand_relative_scale_upper": 1.02,
    "local_mano_articulation_frozen": true,
    "require_noise_pred_obj_scheduler_step_proof": true
  },
  "rollback": {
    "nonfinite_state": true,
    "positive_depth_failure": true,
    "hand_identity_change": true,
    "anchor_trust_region_violation": true,
    "object_articulation_collapse": true,
    "material_object_geometry_regression": true
  },
  "output_directories": {
    "pre_object": null,
    "post_object": null,
    "post_joint": null,
    "post_gate_d": null,
    "final_selected": null
  },
  "authorizes_object_only_execution": false,
  "authorizes_joint_flow_execution": false,
  "authorizes_gate_d_execution": false
}
JSON

"$ACTIVE_PYTHON" - "$SEVEN_DOF_RESULT" > "$HANDOFF_ROOT/evidence/seven_dof_npz_inventory.txt" <<'PY'
import sys
from pathlib import Path
import numpy as np

path = Path(sys.argv[1])
with np.load(path, allow_pickle=False) as data:
    print(f"path={path}")
    for key in data.files:
        value = data[key]
        print(f"{key}: shape={value.shape} dtype={value.dtype}")
PY

cat > "$HANDOFF_ROOT/launch/README_NEXT.txt" <<EOF2
Preparation is complete. No optimizer has been executed.

Next manual actions:
1. Edit $PIPE_TARGET to add the opt-in external-anchor seam.
2. Keep default behavior unchanged when the feature is off.
3. Convert the frozen s100_up state into the exact centered MoGe convention.
4. Export the pipeline's 778 hand vertices before any optimization.
5. Compare them against the source-frozen anchor vertices with a versioned tolerance.
6. Fill launch_contract.template.json, hash every bound input, and request review.
7. Authorize object-only execution only after the roundtrip and static audit pass.
EOF2

echo "[PASS] HANDOFF_PREPARATION_ROOT=$HANDOFF_ROOT"
echo "[HOLD] GPU_EXECUTION_NOT_AUTHORIZED"
}

main "$@"
