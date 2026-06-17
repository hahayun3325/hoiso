#!/usr/bin/env bash
set -euo pipefail

cd /home/fredcui/Projects/FollowMyHold
export PHASE1_OUT="/home/fredcui/foho_phase0/phase1_diagnostics"

mkdir -p "$PHASE1_OUT/selector_v4_pipeline_dryrun"
mkdir -p "$PHASE1_OUT/selector_v4_action_simulation"
mkdir -p "$PHASE1_OUT/selector_v4_selected_only_outputs"

echo "[1/4] Run selector-v4 decision gate"
python scripts/phase1/run_selector_v4_pipeline_dryrun.py \
  | tee "$PHASE1_OUT/selector_v4_pipeline_dryrun/run_selector_v4_selected_only_gate_decision.log"

echo "[2/4] Run action simulation"
python scripts/phase1/selector_v4_action_simulation.py \
  | tee "$PHASE1_OUT/selector_v4_action_simulation/run_selector_v4_selected_only_gate_action.log"

echo "[3/4] Create selected-output-only final folder"
python scripts/phase1/selector_v4_selected_only_replacement.py \
  | tee "$PHASE1_OUT/selector_v4_selected_only_outputs/run_selector_v4_selected_only_gate_replacement.log"

echo "[4/4] Validate selected-output-only outputs"
python scripts/phase1/validate_selector_v4_selected_only.py \
  | tee "$PHASE1_OUT/selector_v4_selected_only_outputs/run_selector_v4_selected_only_gate_validation.log"

echo "[OK] selector-v4 selected-output-only gate completed"
