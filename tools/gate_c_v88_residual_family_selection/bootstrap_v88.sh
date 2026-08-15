#!/usr/bin/env bash
set -u

REPO="${REPO:-/home/fredcui/Projects/FollowMyHold}"
DATA="${DATA:-/home/fredcui/foho_phase0}"
CASE_ROOT="${CASE_ROOT:-$DATA/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2}"
METHOD_ROOT="${METHOD_ROOT:-$CASE_ROOT/gate_c1_physical_hand_placement_method_v27}"
V88_ROOT="${V88_ROOT:-$METHOD_ROOT/v3_next_placement_family_selection_v88}"

mkdir -p \
  "$V88_ROOT/config" \
  "$V88_ROOT/evidence" \
  "$V88_ROOT/reports" \
  "$V88_ROOT/run" \
  "$V88_ROOT/visuals" \
  "$V88_ROOT/notes" \
  "$V88_ROOT/hashes"

cat > "$V88_ROOT/config/next_family_selection_scope_v88.json" <<'JSON'
{
  "schema": "next_placement_family_selection_scope_v88",
  "case_id": "alapuse02v3n60",
  "source_route": "close_combined_translation_articulation_capacity_select_next_family",
  "allowed": [
    "freeze_v87",
    "subspace_vs_bound_audit",
    "per_joint_residual_audit",
    "residual_morphology_audit",
    "alternate_candidate_inventory",
    "one_next_family_policy"
  ],
  "closed": [
    "reweight_and_rerun_v87_without_preregistration",
    "increase_v87_bounds_post_hoc",
    "nonlinear_optimizer",
    "nonzero_mesh",
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

printf '[PASS] V88_ROOT=%s\n' "$V88_ROOT"
printf '[PASS] V88_SCOPE=%s\n' "$V88_ROOT/config/next_family_selection_scope_v88.json"
printf '[HOLD] OPTIMIZER_AUTHORIZED=false\n'
