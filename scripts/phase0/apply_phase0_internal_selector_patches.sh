#!/usr/bin/env bash
set -euo pipefail

cd /home/fredcui/Projects/FollowMyHold

python scripts/phase0/apply_internal_phase42_selector_state_patch.py
python scripts/phase0/apply_internal_phase42_auto_selector_patch.py
python scripts/phase0/fix_internal_phase42_auto_selector_before_mesh_v3.py

python -m py_compile third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py

grep -n \
  "FOHO_INTERNAL_SELECTOR_AUTO\|auto_fragmentation\|saved before_phase42 mesh at step" \
  third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py

echo "[OK] Phase 0 internal selector patches applied."
