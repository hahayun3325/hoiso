#!/usr/bin/env bash
set -euo pipefail

cd /home/fredcui/Projects/FollowMyHold

export AKET_ATTEMPT0="/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_aket01_partaware_v2/attempt0_partaware_prompt"
export NEW_RUN_ID="arctic_aket01_partaware_v2_attempt0"
export NEW_ENV="configs/generated/pipeline.phase1.${NEW_RUN_ID}.env"

source "$NEW_ENV"

echo "[RUN_ID] $RUN_ID"
echo "[OUTPUT_DIR] $OUTPUT_DIR"
echo "[FOHO_RUN_DIR] $FOHO_RUN_DIR"
echo "[GEMINI_RESPONSES] $GEMINI_RESPONSES"

# Replace the line below with the exact launcher used for the previous ARCTIC run.
# Example pattern:
# bash scripts/phase0/<YOUR_EXISTING_ARCTIC_RUN_SCRIPT>.sh

echo "[TODO] Insert the existing FMH/ARCTIC launcher here."
exit 1
