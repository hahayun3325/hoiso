#!/usr/bin/env bash
set -euo pipefail

cd /home/fredcui/Projects/FollowMyHold

source "$HOME/anaconda3/etc/profile.d/conda.sh"
conda activate foho
source ~/.foho_secrets

export SRC="$HOME/foho_phase0/runs/smoke_015_prompt_rect"
export DST="$HOME/foho_phase0/runs/smoke_016_prompt_rect_guidance_ultralow"

rm -rf "$DST"
mkdir -p "$DST/guidance_out" "$DST/foho_debug"

for d in \
  ours_inpaint \
  cropped_hand_masks \
  moge_out \
  hunyuan_hoi_out \
  hamer_out \
  h2m_transformations \
  aligned_mano
do
  ln -sfn "$SRC/$d" "$DST/$d"
done

export PYTHONPATH=src
export CUDA_HOME="/usr/local/cuda"
export CUDA_VISIBLE_DEVICES=0
export FOHO_DEBUG_DIR="$DST/foho_debug"
export PYTORCH_CUDA_ALLOC_CONF="backend:cudaMallocAsync"

export FOHO_RENDER_SCALE=1.0
export FOHO_RENDER_FACES_PER_PIXEL=1
export FOHO_SIL_FACES_PER_PIXEL=3

export FOHO_NUM_INFERENCE_STEPS=6
export FOHO_OPT_STEPS_HAND=20
export FOHO_OPT_STEPS_SCALE=10
export FOHO_OPT_STEPS_JOINT=5

export FOHO_FINAL_OCTREE_RES=128

PYTHONPATH=src python3 -m foho.guidance.run \
  --project_root "/home/fredcui/Projects/FollowMyHold" \
  --cropped_obj_img_dir "$DST/ours_inpaint" \
  --mask_dir "$DST/cropped_hand_masks" \
  --moge_out_dir "$DST/moge_out" \
  --hunyuan_hoi_mesh_dir "$DST/hunyuan_hoi_out" \
  --hamer_out_dir "$DST/hamer_out" \
  --h2m_rt_dir "$DST/h2m_transformations" \
  --aligned_mano_dir "$DST/aligned_mano" \
  --guidance_out_dir "$DST/guidance_out" \
  |& tee ~/foho_phase0/logs/phase0_16_prompt_rect_guidance_ultralow.log
