#!/usr/bin/env bash
set -euo pipefail

: "${REPO:=/home/fredcui/Projects/FollowMyHold}"
: "${DATA:=/home/fredcui/foho_phase0}"
: "${CASE_ROOT:=$DATA/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2}"
: "${TOOL_ROOT:=$REPO/tools/gate_c_v57_dual_read_only}"
: "${AUDIT_ROOT:=$CASE_ROOT/gate_c1_5_v57_dual_read_only_alignment_audit}"

mkdir -p "$AUDIT_ROOT"/{config,inventory,root_audit,articulation_probe,decision,hashes,notes}

for src in \
  "$TOOL_ROOT/config/root_audit_thresholds.json" \
  "$TOOL_ROOT/templates/object_lineage_manifest.csv" \
  "$TOOL_ROOT/templates/low_memory_schedule.json"; do
  dst="$AUDIT_ROOT/config/$(basename "$src")"
  if [[ ! -e "$dst" ]]; then cp "$src" "$dst"; fi
done

find "$CASE_ROOT" -type f \
  \( -iname '*.ply' -o -iname '*.obj' -o -iname '*.glb' -o -iname '*.npy' -o -iname '*.json' -o -iname '*.csv' \) \
  2>/dev/null | rg -i 'gate.?a|part|vmap|vertex.?map|object|hunyuan|canonical|assembled|screen|lid|keyboard|base|transform|scale' \
  | sort -u > "$AUDIT_ROOT/inventory/object_and_lineage_artifacts.txt" || true

find "$REPO" -type f \
  \( -iname '*.py' -o -iname '*.sh' -o -iname '*.json' \) \
  2>/dev/null | rg -i 'source_bound_zero_adapter_v56|articulation_adequacy|mano.*forward|project_keypoints' \
  | sort -u > "$AUDIT_ROOT/inventory/source_forward_artifacts.txt" || true

printf '[PASS] V57_AUDIT_ROOT=%s\n' "$AUDIT_ROOT"
printf '[INFO] EDIT=%s\n' "$AUDIT_ROOT/config/object_lineage_manifest.csv"
printf '[INFO] REVIEW=%s\n' "$AUDIT_ROOT/inventory/object_and_lineage_artifacts.txt"
printf '[HOLD] NO_NONZERO_WORK_AUTHORIZED\n'
