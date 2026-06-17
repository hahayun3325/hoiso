#!/usr/bin/env bash
set -euo pipefail

cd /home/fredcui/Projects/FollowMyHold
export PHASE1_OUT="/home/fredcui/foho_phase0/phase1_diagnostics"

mkdir -p "$PHASE1_OUT/selector_v4_pipeline_dryrun"
mkdir -p "$PHASE1_OUT/selector_v4_smoke"

echo "[1/2] Run selector-v4 pipeline dry-run"
python scripts/phase1/run_selector_v4_pipeline_dryrun.py \
  | tee "$PHASE1_OUT/selector_v4_pipeline_dryrun/run_selector_v4_pipeline_dryrun_smoke.log"

echo "[2/2] Check smoke decisions"
python scripts/phase1/check_selector_v4_smoke_decisions.py \
  | tee "$PHASE1_OUT/selector_v4_smoke/run_selector_v4_smoke_decision_check_latest.log"

echo "[OK] selector-v4 smoke gate completed"
