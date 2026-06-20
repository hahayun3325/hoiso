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

# Required reruns first.
CASES=("abox01" "ascis01" "amicuse01")

for CASE in "${CASES[@]}"
do
  NEW_RUN_ID="arctic_${CASE}_partaware_v2_attempt0"
  ATTEMPT_ROOT="/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_${CASE}_partaware_v2/attempt0_partaware_prompt"
  CFG="configs/generated/pipeline.phase1.${NEW_RUN_ID}.env"
  LOG="$ATTEMPT_ROOT/logs/${NEW_RUN_ID}.log"

  echo
  echo "============================================================"
  echo "[RUN] $CASE"
  echo "[CFG] $CFG"
  echo "[LOG] $LOG"
  echo "============================================================"

  test -s "$CFG" || { echo "[BAD] missing config $CFG"; exit 1; }

  source "$CFG"

  if [[ "$RUN_ID" != "$NEW_RUN_ID" ]]; then
    echo "[BAD] RUN_ID mismatch: $RUN_ID vs $NEW_RUN_ID"
    exit 1
  fi

  if [[ "$OUTPUT_DIR" != *"runs_prompt_refined_v2"* ]]; then
    echo "[BAD] OUTPUT_DIR does not point to prompt-refined root: $OUTPUT_DIR"
    exit 1
  fi

  mkdir -p "$OUTPUT_DIR"
  mkdir -p "$ATTEMPT_ROOT/logs"

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
done
