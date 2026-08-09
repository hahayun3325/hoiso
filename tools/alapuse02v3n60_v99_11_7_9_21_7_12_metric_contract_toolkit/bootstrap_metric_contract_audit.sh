#!/usr/bin/env bash
set -u

: "${CASE_ROOT:?Set CASE_ROOT to the alapuse02v3n60_auto_v2 case root}"

AUDIT_ROOT="${AUDIT_ROOT:-$CASE_ROOT/gate_c_hand_anchor/v99_11_7_9_21_7_12_metric_contract_diagnosis}"
TOOL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p \
  "$AUDIT_ROOT/config" \
  "$AUDIT_ROOT/evidence" \
  "$AUDIT_ROOT/reports" \
  "$AUDIT_ROOT/visuals" \
  "$AUDIT_ROOT/hashes" \
  "$AUDIT_ROOT/notes"

SCOPE="$AUDIT_ROOT/config/scope_v99_11_7_9_21_7_12.json"
if [[ ! -e "$SCOPE" ]]; then
  cat > "$SCOPE" <<'JSON'
{
  "schema": "metric_contract_diagnosis_scope_v99_11_7_9_21_7_12",
  "allowed": [
    "freeze_existing_evidence",
    "candidate_binding_audit",
    "depth_coordinate_frame_review",
    "v6_v3_metric_distribution_audit",
    "full_raster_joint_overlay",
    "gate_stage_role_review",
    "paired_analyzer_policy_preparation_if_required"
  ],
  "closed": [
    "fit_thresholds_on_v3",
    "select_least_bad_v3_crop",
    "blindly_apply_translation_xyz_to_h2m_vertices",
    "new_hamer_execution",
    "hand_optimization",
    "contact",
    "collision",
    "flow",
    "C2",
    "F3_4",
    "Gate_D"
  ],
  "authorizes_metric_change": false,
  "authorizes_candidate_selection": false,
  "authorizes_optimizer": false
}
JSON
  echo "[PASS] CREATED_SCOPE=$SCOPE"
else
  echo "[INFO] SCOPE_EXISTS=$SCOPE"
fi

for template in \
  frame_contract_review.template.json \
  candidate_binding_manifest.template.csv; do
  src="$TOOL_ROOT/config/$template"
  dst="$AUDIT_ROOT/config/${template/.template/}"
  if [[ -f "$src" && ! -e "$dst" ]]; then
    cp "$src" "$dst"
    echo "[PASS] CREATED_TEMPLATE=$dst"
  fi
done

echo "[INFO] AUDIT_ROOT=$AUDIT_ROOT"
echo "[INFO] This bootstrap authorizes no metric change, selection, or optimization."
