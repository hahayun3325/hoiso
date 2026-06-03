#!/usr/bin/env bash
set -euo pipefail

BASE_RUN_ID="${1:?Usage: bash run_oakink_internal_selector_debug_one.sh <base_run_id>}"
DEBUG_RUN_ID="${BASE_RUN_ID}_selector_debug"

cd /home/fredcui/Projects/FollowMyHold

source "$HOME/anaconda3/etc/profile.d/conda.sh"
conda activate foho
source ~/.foho_secrets

python scripts/phase0/apply_internal_selector_debug_export_patch.py

export PYTORCH_CUDA_ALLOC_CONF="backend:cudaMallocAsync"
export GEMINI_MODEL="gemini-2.5-flash"

export FOHO_NUM_INFERENCE_STEPS=6
export FOHO_OPT_STEPS_HAND=20
export FOHO_OPT_STEPS_SCALE=10
export FOHO_OPT_STEPS_JOINT=5
export FOHO_FINAL_OCTREE_RES=192

export FOHO_SELECTOR_DEBUG_DIR="$HOME/foho_phase0/inspection/oakink_000/${DEBUG_RUN_ID}/internal_selector_debug"
mkdir -p "$FOHO_SELECTOR_DEBUG_DIR"

BASE_CFG="configs/generated/pipeline.phase0.${BASE_RUN_ID}.env"
DEBUG_CFG="configs/generated/pipeline.phase0.${DEBUG_RUN_ID}.env"

if [ ! -f "$BASE_CFG" ]; then
  echo "[ERROR] missing base config: $BASE_CFG"
  exit 1
fi

cp "$BASE_CFG" "$DEBUG_CFG"

python - <<PY
from pathlib import Path

base = "${BASE_RUN_ID}"
debug = "${DEBUG_RUN_ID}"
p = Path("${DEBUG_CFG}")
s = p.read_text()

s = s.replace(
    f'BASE_DIR="/home/fredcui/foho_phase0/runs/{base}"',
    f'BASE_DIR="/home/fredcui/foho_phase0/runs/{debug}"'
)
s = s.replace(
    f'FOHO_DEBUG_DIR="/home/fredcui/foho_phase0/runs/{base}/foho_debug"',
    f'FOHO_DEBUG_DIR="/home/fredcui/foho_phase0/runs/{debug}/foho_debug"'
)
s = s.replace(
    f'GEMINI_RESPONSES="/home/fredcui/foho_phase0/runs/{base}/manual_gemini_responses.csv"',
    f'GEMINI_RESPONSES="/home/fredcui/foho_phase0/runs/{debug}/manual_gemini_responses.csv"'
)
p.write_text(s)
print("[OK] wrote", p)
PY

python scripts/phase0/seed_oakink000_preprocess_from_baseline.py \
  --run_id "$DEBUG_RUN_ID" \
  --clean_downstream

cp "$HOME/foho_phase0/runs/${BASE_RUN_ID}/manual_gemini_responses.csv" \
   "$HOME/foho_phase0/runs/${DEBUG_RUN_ID}/manual_gemini_responses.csv"

PYTHONPATH=src python3 -m foho.main \
  --config "$DEBUG_CFG" \
  |& tee "$HOME/foho_phase0/logs/${DEBUG_RUN_ID}.log"

python scripts/phase0/score_internal_selector_debug_exports.py \
  --debug_dir "$FOHO_SELECTOR_DEBUG_DIR" \
  | tee "$HOME/foho_phase0/logs/${DEBUG_RUN_ID}_internal_selector_scores.log"

python scripts/phase0/make_internal_selector_debug_panel.py \
  --debug_dir "$FOHO_SELECTOR_DEBUG_DIR" \
  --out "$FOHO_SELECTOR_DEBUG_DIR/internal_selector_debug_panel.jpg" \
  | tee "$HOME/foho_phase0/logs/${DEBUG_RUN_ID}_internal_selector_panel.log"

echo "[OK] finished $DEBUG_RUN_ID"
echo "[INFO] debug_dir=$FOHO_SELECTOR_DEBUG_DIR"
