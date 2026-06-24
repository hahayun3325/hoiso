#!/usr/bin/env bash
set -euo pipefail

cd /home/fredcui/Projects/FollowMyHold

source ~/anaconda3/etc/profile.d/conda.sh
conda activate foho

export DATA="/home/fredcui/foho_phase0"
export PHASE2_ROOT="$DATA/phase2_gateA_part_recon"

python scripts/phase2/check_gate_a_inputs.py
python scripts/phase2/validate_manual_part_schema.py
python scripts/phase2/flatten_manual_part_schema.py

echo "[OK] Gate A inputs and manual part schema are ready."
echo "[NEXT] Implement or adapt PartField/SAM2 part separation using:"
echo "      $PHASE2_ROOT/gate_a_cases.csv"
echo "      $PHASE2_ROOT/manual_part_schema/arctic5_manual_part_schema_flat.csv"
