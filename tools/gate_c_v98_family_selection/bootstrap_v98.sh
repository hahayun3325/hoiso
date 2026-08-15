#!/usr/bin/env bash
set -u

: "${METHOD_ROOT:?Set METHOD_ROOT to the Gate-C method root}"
V98_ROOT="${V98_ROOT:-$METHOD_ROOT/v3_expanded_placement_family_policy_v98}"
TOOL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p \
  "$V98_ROOT/config" \
  "$V98_ROOT/evidence" \
  "$V98_ROOT/reports" \
  "$V98_ROOT/visuals" \
  "$V98_ROOT/notes" \
  "$V98_ROOT/hashes"

cp -n "$TOOL_ROOT/config/residual_morphology_policy_v98.json" \
  "$V98_ROOT/config/residual_morphology_policy_v98.json" 2>/dev/null || true
cp -n "$TOOL_ROOT/config/candidate_expanded_families_v98.json" \
  "$V98_ROOT/config/candidate_expanded_families_v98.json" 2>/dev/null || true
cp -n "$TOOL_ROOT/templates/selected_family_policy_v98.template.json" \
  "$V98_ROOT/config/selected_family_policy_v98.template.json" 2>/dev/null || true

cat > "$V98_ROOT/config/expanded_family_selection_scope_v98.json" <<'EOF'
{
  "schema": "expanded_placement_family_selection_scope_v98",
  "case_id": "alapuse02v3n60",
  "source_classification": "bounds_likely_limiting",
  "allowed": [
    "freeze_and_hash_v97_1",
    "recover_weighting_contract",
    "read_only_residual_morphology_audit",
    "candidate_family_definition",
    "source_seam_review",
    "family_bound_preregistration"
  ],
  "closed": [
    "new_derivative_collection",
    "optimizer",
    "new_nonzero_pose",
    "automatic_bound_widening",
    "reuse_rejected_branch_e_delta",
    "reuse_v87_diagnostic_solution",
    "contact",
    "collision",
    "flow",
    "C2",
    "F3_4",
    "Gate_D",
    "final_alignment_claim"
  ],
  "authorizes_derivative_collection": false,
  "authorizes_optimizer": false
}
EOF

printf '[PASS] V98_ROOT=%s\n' "$V98_ROOT"
printf '[PASS] V98_SCOPE=%s\n' "$V98_ROOT/config/expanded_family_selection_scope_v98.json"
printf '[HOLD] New derivatives and optimizer remain unauthorized.\n'
