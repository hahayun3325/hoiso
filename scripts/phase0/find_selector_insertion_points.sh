#!/usr/bin/env bash
set -euo pipefail

OUT="$HOME/foho_phase0/inspection/phase017_selector_insertion_points.txt"
mkdir -p "$(dirname "$OUT")"

{
  echo "===== likely optimization / guidance files ====="
  grep -RIlE "Joint optimization|optimizing object|object transformation|step_final|latent2sdf|FlexiCubes" src/foho || true

  echo ""
  echo "===== exact lines ====="
  grep -RInE "Joint optimization|optimizing object|object transformation|step_final|latent2sdf|FlexiCubes" src/foho || true

  echo ""
  echo "===== output writing lines ====="
  grep -RInE "test_obj|test_hand|guidance_out|final_obj_mesh|final_hand_mesh|export" src/foho || true
} | tee "$OUT"
