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

mkdir -p "$HOME/foho_phase0/logs"

for CASE in abox01 aket01 ascis01 alapuse01 amicuse01
do
  RUN_ID="arctic_${CASE}_default"
  RUN="$HOME/foho_phase0/runs/$RUN_ID"
  CFG="configs/generated/pipeline.phase0.${RUN_ID}.env"
  LOG="$HOME/foho_phase0/logs/${RUN_ID}.log"

  echo ""
  echo "========================================"
  echo "RUN $RUN_ID"
  echo "========================================"

  test -s "$CFG" || { echo "[BAD] missing config $CFG"; exit 1; }

  rm -rf \
    "$RUN/original_imgs" \
    "$RUN/masked_obj_imgs" \
    "$RUN/cropped_hoi_imgs" \
    "$RUN/cropped_hoi_imgs_wo_bckg" \
    "$RUN/ours_inpaint" \
    "$RUN/cropped_hand_masks" \
    "$RUN/moge_out" \
    "$RUN/hunyuan_hoi_out" \
    "$RUN/hamer_out" \
    "$RUN/h2m_transformations" \
    "$RUN/aligned_mano" \
    "$RUN/guidance_out" \
    "$RUN/foho_debug"

  mkdir -p "$RUN"

  PYTHONPATH=src python3 -m foho.main \
    --config "$CFG" \
    |& tee "$LOG"
done
