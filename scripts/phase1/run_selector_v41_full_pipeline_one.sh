#!/usr/bin/env bash
set -euo pipefail

CASE="${1:?Usage: scripts/phase1/run_selector_v41_full_pipeline_one.sh <case>}"

cd /home/fredcui/Projects/FollowMyHold

source "$HOME/anaconda3/etc/profile.d/conda.sh"
conda activate foho
source ~/.foho_secrets

export GEMINI_MODEL="gemini-2.5-flash"
export PYTORCH_CUDA_ALLOC_CONF="backend:cudaMallocAsync"
export FOHO_RENDER_SCALE=1.0
export FOHO_RENDER_FACES_PER_PIXEL=1
export FOHO_SIL_FACES_PER_PIXEL=3
export FOHO_NUM_INFERENCE_STEPS=6
export FOHO_OPT_STEPS_HAND=20
export FOHO_OPT_STEPS_SCALE=10
export FOHO_OPT_STEPS_JOINT=5
export FOHO_FINAL_OCTREE_RES=192

RUN_ID="arctic_${CASE}_selector_v41_refined_pipeline"
CFG="configs/generated/pipeline.phase1.${RUN_ID}.env"
RUN_ROOT="/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/${RUN_ID}"
LOG="$RUN_ROOT/${RUN_ID}.log"

echo "[RUN] $CASE"
echo "[CFG] $CFG"
echo "[LOG] $LOG"

test -s "$CFG" || { echo "[BAD] missing config $CFG"; exit 1; }

mkdir -p "$RUN_ROOT"

# Source config so we can check GEMINI_RESPONSES before running.
source "$CFG"

test -s "$GEMINI_RESPONSES" || {
  echo "[BAD] missing or empty GEMINI_RESPONSES: $GEMINI_RESPONSES"
  exit 1
}

echo "[OK] GEMINI_RESPONSES=$GEMINI_RESPONSES"

PYTHONPATH=src python3 -m foho.main \
  --config "$CFG" \
  |& tee "$LOG"
