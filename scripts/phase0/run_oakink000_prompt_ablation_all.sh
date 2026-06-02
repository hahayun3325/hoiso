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

RUNS=(
  oakink000_default
  oakink000_gpt54thinking_template
  oakink000_gpt54_template
  oakink000_sonar2_template
  oakink000_gemini31pro_template
  oakink000_sonnet46_template
  oakink000_sonnet46thinking_template
  oakink000_nemotron3super_template
)

for RUN_ID in "${RUNS[@]}"; do
  CFG="configs/generated/pipeline.phase0.${RUN_ID}.env"
  RUN_DIR="$HOME/foho_phase0/runs/${RUN_ID}"
  LOG="$HOME/foho_phase0/logs/${RUN_ID}.log"

  echo ""
  echo "===== RUN ${RUN_ID} ====="

  if [ ! -f "$CFG" ]; then
    echo "[SKIP] missing config: $CFG"
    continue
  fi

  python scripts/phase0/seed_oakink000_preprocess_from_baseline.py \
    --run_id "$RUN_ID" \
    --clean_downstream \
    | tee "$HOME/foho_phase0/logs/${RUN_ID}_seed_preprocess.log"

  PYTHONPATH=src python3 -m foho.main \
    --config "$CFG" \
    |& tee "$LOG"

  python scripts/phase0/apply_selector_with_compat.py \
    "$RUN_DIR" \
    |& tee "$HOME/foho_phase0/logs/${RUN_ID}_selector.log" || true
done

python scripts/phase0/summarize_oakink000_prompt_runs.py \
  | tee "$HOME/foho_phase0/logs/oakink000_prompt_run_summary.log"
