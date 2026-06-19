#!/usr/bin/env bash
set -euo pipefail

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

export NEW_RUN_ID="arctic_aket01_partaware_v2_attempt0"
export AKET_ATTEMPT0="/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_aket01_partaware_v2/attempt0_partaware_prompt"
export CFG="configs/generated/pipeline.phase1.${NEW_RUN_ID}.env"
export LOG="$AKET_ATTEMPT0/logs/${NEW_RUN_ID}.log"

test -s "$CFG" || { echo "[BAD] missing config $CFG"; exit 1; }

# Source only for printing sanity checks. The pipeline itself also receives --config "$CFG".
source "$CFG"

echo "[RUN_ID] $RUN_ID"
echo "[OUTPUT_DIR] $OUTPUT_DIR"
echo "[FOHO_RUN_DIR] $FOHO_RUN_DIR"
echo "[GEMINI_RESPONSES] $GEMINI_RESPONSES"
echo "[CFG] $CFG"
echo "[LOG] $LOG"

if [[ "$RUN_ID" != "$NEW_RUN_ID" ]]; then
  echo "[BAD] RUN_ID mismatch: $RUN_ID vs $NEW_RUN_ID"
  exit 1
fi

if [[ "$OUTPUT_DIR" != *"runs_prompt_refined_v2"* ]]; then
  echo "[BAD] OUTPUT_DIR does not point to prompt-refined output root: $OUTPUT_DIR"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
mkdir -p "$AKET_ATTEMPT0/logs"

# Clean only this new attempt0 output folder, never old Phase 0/Phase 1 runs.
rm -rf \
  "$OUTPUT_DIR/original_imgs" \
  "$OUTPUT_DIR/masked_obj_imgs" \
  "$OUTPUT_DIR/cropped_hoi_imgs" \
  "$OUTPUT_DIR/cropped_hoi_imgs_wo_bckg" \
  "$OUTPUT_DIR/ours_inpaint" \
  "$OUTPUT_DIR/cropped_hand_masks" \
  "$OUTPUT_DIR/moge_out" \
  "$OUTPUT_DIR/hunyuan_hoi_out" \
  "$OUTPUT_DIR/hamer_out" \
  "$OUTPUT_DIR/h2m_transformations" \
  "$OUTPUT_DIR/aligned_mano" \
  "$OUTPUT_DIR/guidance_out" \
  "$OUTPUT_DIR/foho_debug"

PYTHONPATH=src python3 -m foho.main \
  --config "$CFG" \
  |& tee "$LOG"
