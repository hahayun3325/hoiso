#!/usr/bin/env bash
set -euo pipefail

OUT="$HOME/foho_phase0/inspection/phase017_inventory/spam_prompt_selector_assets.txt"
mkdir -p "$(dirname "$OUT")"

{
  echo "===== known SPAM input candidates ====="
  ls -lh "$HOME/foho_phase0/inputs/test_hoi_clean_002.jpg" 2>/dev/null || true
  find "$HOME/foho_phase0/inputs" -maxdepth 3 -type f \
    \( -iname "*spam*" -o -iname "*hoi_clean*" -o -iname "*gpfm*" \) \
    -ls 2>/dev/null || true

  echo ""
  echo "===== smoke013 baseline assets ====="
  find "$HOME/foho_phase0" -type f \
    \( -path "*smoke*013*" -o -path "*smoke_013*" \) \
    \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.ply" \) \
    | sort || true

  echo ""
  echo "===== smoke015 structured prompt assets ====="
  find "$HOME/foho_phase0" -type f \
    \( -path "*smoke*015*" -o -path "*smoke_015*" \) \
    \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.ply" \) \
    | sort || true

  echo ""
  echo "===== smoke016/017 fragmented final assets ====="
  find "$HOME/foho_phase0" -type f \
    \( -path "*smoke*016*" -o -path "*smoke_016*" -o -path "*smoke*017*" -o -path "*smoke_017*" \) \
    \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.ply" \) \
    | sort || true

  echo ""
  echo "===== smoke022 selector/fallback assets ====="
  find "$HOME/foho_phase0/runs/smoke_022_freeze_obj_pose_and_noise" -maxdepth 5 -type f \
    \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.ply" -o -iname "*.json" \) \
    | sort || true

  echo ""
  echo "===== existing prompt comparison sheets ====="
  find "$HOME/foho_phase0/inspection" -type f \
    \( -iname "*prompt*sheet*.jpg" -o -iname "*smoke013*015*016*017*.jpg" -o -iname "*comparison_sheet*.jpg" \) \
    | sort || true
} | tee "$OUT"
