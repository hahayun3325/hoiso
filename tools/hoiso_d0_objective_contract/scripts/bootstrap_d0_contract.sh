#!/usr/bin/env bash
set -euo pipefail
: "${PROJECT_ROOT:=/home/fredcui/Projects/FollowMyHold}"
: "${DATA_ROOT:=/home/fredcui/foho_phase0}"
: "${CASE_ROOT:=$DATA_ROOT/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2}"
TOOL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
D0_ROOT="$CASE_ROOT/gate_d0_contact_contract_v1"
mkdir -p "$D0_ROOT"/{config,evidence,semantic,compiled,objectives,zorder,reports,receipts,hashes,notes}
cp -n "$TOOL_ROOT/templates/gate_d0_query.md" "$D0_ROOT/semantic/gate_d0_query.md" || true
cp -n "$TOOL_ROOT/templates/gate_d1_query.md" "$D0_ROOT/semantic/gate_d1_query.md" || true
cp -n "$TOOL_ROOT/schemas/gate_d0_semantic.schema.json" "$D0_ROOT/config/" || true
cp -n "$TOOL_ROOT/config/finger_geometry_map.template.json" "$D0_ROOT/config/finger_geometry_map.json" || true
cp -n "$TOOL_ROOT/config/object_patch_map.template.json" "$D0_ROOT/config/object_patch_map.json" || true
cp -n "$TOOL_ROOT/config/objective_policy.template.json" "$D0_ROOT/config/objective_policy.json" || true
cp -n "$TOOL_ROOT/templates/prompt_registry_manifest.template.json" "$D0_ROOT/config/prompt_registry_manifest.json" || true
{
  echo "# Gate B / D0 / D1 source trace"
  rg -n -i 'gate.?b|gate.?d0|gate.?d1|candidate.?finger|contact.?proposal|forbidden.?contact|screen_lid|keyboard_base' \
    "$PROJECT_ROOT/docs" "$PROJECT_ROOT/scripts" "$PROJECT_ROOT/src" "$PROJECT_ROOT/tools" \
    -g '*.md' -g '*.json' -g '*.py' -g '*.sh' 2>/dev/null | head -500 || true
} > "$D0_ROOT/evidence/contact_source_trace.txt"
{
  echo "# Optimization and step-control trace"
  rg -n -C 5 'optimization_steps_scale|FOHO_OPT_STEPS_SCALE|FOHO_.*STEPS|hand.*steps|object.*steps|joint.*steps|noise_pred_obj|scheduler\.step|range\(' \
    "$PROJECT_ROOT/third_party/Hunyuan3D-2/hy3dgen/shapegen" "$PROJECT_ROOT/src/foho" "$PROJECT_ROOT/scripts/phase2" \
    -g '*.py' -g '*.sh' 2>/dev/null | head -800 || true
} > "$D0_ROOT/evidence/optimization_step_source_trace.txt"
cat > "$D0_ROOT/config/d0_scope.json" <<JSON
{
  "schema": "hoiso_d0_scope_v1",
  "case_root": "$CASE_ROOT",
  "canonical_order": ["Gate_C", "Gate_D0", "technical_zero", "hand", "object_audit_optional_object", "joint", "Gate_D1"],
  "authorizes_mllm_query": false,
  "authorizes_geometry_compilation": false,
  "authorizes_optimizer": false
}
JSON
find "$D0_ROOT/config" "$D0_ROOT/semantic" -type f -print0 | sort -z | xargs -0 sha256sum > "$D0_ROOT/hashes/bootstrap_inputs.sha256"
echo "[PASS] D0_ROOT=$D0_ROOT"
echo "[HOLD] complete semantic response, geometry maps, z-order owner, and zero replay before any optimizer"
