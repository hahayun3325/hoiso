#!/usr/bin/env bash
set -euo pipefail

OUT="/home/fredcui/datasets/hoi/dexycb/raw"
LOG="$HOME/foho_phase0/inspection/eval_scripts/dexycb_minimal_by_id_download.log"

mkdir -p "$OUT" "$(dirname "$LOG")"
cd "$OUT"

download_one () {
  local name="$1"
  local id="$2"

  echo ""
  echo "===== downloading $name =====" | tee -a "$LOG"

  # Remove tiny invalid previous files.
  if [ -f "$name" ]; then
    size=$(stat -c%s "$name")
    if [ "$size" -lt 1048576 ] && [ "$name" != "calibration.tar.gz" ]; then
      echo "[WARN] removing tiny invalid $name size=$size" | tee -a "$LOG"
      rm -f "$name"
    fi
  fi

  gdown --continue "$id" -O "$name" |& tee -a "$LOG" || true

  echo "[INFO] file check for $name" | tee -a "$LOG"
  ls -lh "$name" 2>/dev/null | tee -a "$LOG" || true
  file "$name" 2>/dev/null | tee -a "$LOG" || true

  if tar -tzf "$name" >/dev/null 2>&1; then
    echo "[OK] valid gzip tar: $name" | tee -a "$LOG"
  else
    echo "[ERROR] invalid gzip tar: $name" | tee -a "$LOG"
    return 1
  fi
}

# Official DexYCB subject-wise minimal files.
download_one "20200709-subject-01.tar.gz" "1Ehh92wDE3CWAiKG7E9E73HjN2Xk2XfEk" || true
download_one "calibration.tar.gz" "1UAwVKT4Rgb1fLcFoa1o71_-0NtSvvLAQ" || true
download_one "models.tar.gz" "1cAzlQBpcTatI5ykYQ8ziQiHLUG_a_UpM" || true
