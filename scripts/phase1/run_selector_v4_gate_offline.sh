#!/usr/bin/env bash
set -euo pipefail

cd /home/fredcui/Projects/FollowMyHold
export PHASE1_OUT="/home/fredcui/foho_phase0/phase1_diagnostics"

mkdir -p "$PHASE1_OUT/selector_v4_hardgate"

python scripts/phase1/compute_first_contact_metrics.py \
  --config configs/phase1_diagnostics.yaml

python scripts/phase1/compute_penetration_diagnostics.py \
  --phase1-out "$PHASE1_OUT"

python scripts/phase1/compute_object_integrity_metrics.py

python scripts/phase1/selector_v4_hardgate_dryrun.py \
  | tee "$PHASE1_OUT/selector_v4_hardgate/run_selector_v4_hardgate.log"
