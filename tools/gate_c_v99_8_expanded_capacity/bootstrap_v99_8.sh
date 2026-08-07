#!/usr/bin/env bash
set -u

: "${METHOD_ROOT:?Set METHOD_ROOT to the Gate-C method root before running.}"
TOOL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
V99_8_ROOT="${V99_8_ROOT:-$METHOD_ROOT/v3_translation_scale_articulation_capacity_v99_8}"
V99_9_ROOT="${V99_9_ROOT:-$METHOD_ROOT/v3_translation_scale_articulation_capacity_execution_v99_9}"
V99_10_ROOT="${V99_10_ROOT:-$METHOD_ROOT/v3_translation_scale_articulation_capacity_review_v99_10}"

mkdir -p \
  "$V99_8_ROOT/config" "$V99_8_ROOT/evidence" "$V99_8_ROOT/run" "$V99_8_ROOT/reports" "$V99_8_ROOT/hashes" \
  "$V99_9_ROOT/run" "$V99_9_ROOT/reports" "$V99_9_ROOT/hashes" \
  "$V99_10_ROOT/reports"

POLICY="$V99_8_ROOT/config/expanded_capacity_policy_v99_8.json"
if [[ ! -e "$POLICY" ]]; then
  cp "$TOOL_ROOT/config/expanded_capacity_policy_v99_8.template.json" "$POLICY"
  echo "[HOLD] CREATED_POLICY_REVIEW_REQUIRED=$POLICY"
else
  echo "[INFO] PRESERVED_EXISTING_POLICY=$POLICY"
fi

python -m py_compile "$TOOL_ROOT"/scripts/*.py

echo "[PASS] V99_8_WORKSPACE=$V99_8_ROOT"
echo "[PASS] V99_9_WORKSPACE=$V99_9_ROOT"
echo "[PASS] V99_10_WORKSPACE=$V99_10_ROOT"
echo "[HOLD] CAPACITY_EXECUTION_REQUIRES_POLICY_FIELD_authorizes_capacity_execution=true"
echo "[HOLD] OPTIMIZER_EXECUTION_NOT_AUTHORIZED"
