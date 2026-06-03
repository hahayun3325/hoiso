#!/usr/bin/env bash
set -euo pipefail

BASE_RUN_ID="${1:?Usage: bash create_phase42_mock_selector_from_internal_exports.sh <base_run_id>}"

cd /home/fredcui/Projects/FollowMyHold

DEBUG_RUN_ID="${BASE_RUN_ID}_selector_debug"
RUN="$HOME/foho_phase0/runs/${DEBUG_RUN_ID}"
DEBUG_DIR="$HOME/foho_phase0/inspection/oakink_000/${DEBUG_RUN_ID}/internal_selector_debug"
OUT="$HOME/foho_phase0/inspection/oakink_000/${BASE_RUN_ID}/phase42_selector_mock_object_only"

mkdir -p "$OUT"

PHASE42="$(find "$DEBUG_DIR" -maxdepth 1 -name 'phase42_obj_transformed_before_joint_t4_opt0.ply' | head -n 1)"
if [ -z "$PHASE42" ]; then
  PHASE42="$(find "$DEBUG_DIR" -maxdepth 1 -name 'phase42_obj_transformed_before_joint*.ply' | sort | head -n 1)"
fi

FINAL_OBJ="$(find "$RUN/guidance_out" -maxdepth 1 \( -name '*obj*.ply' -o -name 'test_obj.ply' \) | sort | head -n 1)"

echo "[INFO] base_run: $BASE_RUN_ID"
echo "[INFO] phase42: $PHASE42"
echo "[INFO] final_obj: $FINAL_OBJ"

if [ ! -f "$PHASE42" ]; then
  echo "[ERROR] missing Phase 4.2 object candidate"
  exit 1
fi

if [ ! -f "$FINAL_OBJ" ]; then
  echo "[ERROR] missing final object"
  exit 1
fi

PYTHONPATH=src python scripts/phase0/select_phase42_object_candidate.py \
  --out_dir "$OUT" \
  --candidate "phase42_before_joint" "$PHASE42" "phase42_before_joint" \
  --candidate "final_obj" "$FINAL_OBJ" "final_guided"

cat "$OUT/phase42_object_selection_report.json"
