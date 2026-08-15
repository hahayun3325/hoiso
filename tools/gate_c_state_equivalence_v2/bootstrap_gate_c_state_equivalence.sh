#!/usr/bin/env bash
# Read-only/bootstrap inventory for Gate-C state equivalence.
# It creates a versioned audit workspace but never edits source artifacts or launches optimization.

set -u
set -o pipefail

log() { printf '%s\n' "$*"; }
hold() { printf '[HOLD] %s\n' "$*" >&2; }

REPO="${REPO:-/home/fredcui/Projects/FollowMyHold}"
DATA="${DATA:-/home/fredcui/foho_phase0}"
CASE_ROOT="${CASE_ROOT:-$DATA/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2}"
AUDIT_ROOT="${AUDIT_ROOT:-$CASE_ROOT/gate_c0_state_equivalence_v2}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "$REPO" ]]; then
  hold "Repository not found: $REPO"
  exit 1
fi
if [[ ! -d "$CASE_ROOT" ]]; then
  hold "Case root not found: $CASE_ROOT"
  exit 1
fi

mkdir -p \
  "$AUDIT_ROOT/inventory" \
  "$AUDIT_ROOT/manifests" \
  "$AUDIT_ROOT/config" \
  "$AUDIT_ROOT/reports" \
  "$AUDIT_ROOT/decision" \
  "$AUDIT_ROOT/preregistration"

[[ -f "$AUDIT_ROOT/manifests/state_ledger.csv" ]] || \
  cp "$SCRIPT_DIR/templates/state_ledger.csv" "$AUDIT_ROOT/manifests/state_ledger.csv"
[[ -f "$AUDIT_ROOT/config/state_equivalence.env" ]] || \
  cp "$SCRIPT_DIR/templates/state_equivalence.env.template" "$AUDIT_ROOT/config/state_equivalence.env"
[[ -f "$AUDIT_ROOT/config/state_equivalence_thresholds.json" ]] || \
  cp "$SCRIPT_DIR/config/state_equivalence_thresholds.json" "$AUDIT_ROOT/config/state_equivalence_thresholds.json"
[[ -f "$AUDIT_ROOT/preregistration/preregistration_after_state_equivalence.md" ]] || \
  cp "$SCRIPT_DIR/templates/preregistration_after_state_equivalence.md" \
    "$AUDIT_ROOT/preregistration/preregistration_after_state_equivalence.md"

{
  echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "repo=$REPO"
  echo "case_root=$CASE_ROOT"
  echo "audit_root=$AUDIT_ROOT"
  echo "python=$(command -v python || true)"
  echo "python_version=$(python --version 2>&1 || true)"
  echo "conda_default_env=${CONDA_DEFAULT_ENV:-<unset>}"
} > "$AUDIT_ROOT/inventory/runtime_context.txt"

(
  cd "$REPO" || exit 1
  {
    echo "HEAD=$(git rev-parse HEAD 2>/dev/null || echo '<not-a-git-repo>')"
    echo
    echo "--- git status --short ---"
    git status --short 2>/dev/null || true
    echo
    echo "--- git diff --stat ---"
    git diff --stat 2>/dev/null || true
  } > "$AUDIT_ROOT/inventory/git_state.txt"
)

# Search source contracts without assuming exact line numbers or layout.
if command -v rg >/dev/null 2>&1; then
  (
    cd "$REPO" || exit 1
    rg -n -C 4 --hidden --glob '!*.git*' \
      'pred_keypoints_3d|mano_output\.joints|extra_joints_idxs|joint_map|J_regressor|J_regressor_hamer|mano_vert_to_3dkps|handedness|right\]|cam_t|perspective_projection' \
      src third_party third_party_patches 2>/dev/null || true
  ) > "$AUDIT_ROOT/inventory/keypoint_source_contract_hits.txt"
else
  hold "ripgrep (rg) not found; source-contract inventory is empty"
  : > "$AUDIT_ROOT/inventory/keypoint_source_contract_hits.txt"
fi

find "$REPO" "$CASE_ROOT" -type f \
  \( -name '*.npy' -o -name '*.npz' -o -name '*.pt' -o -name '*.pth' \
     -o -name '*.ply' -o -name '*.obj' -o -name '*.json' -o -name '*.png' \
     -o -name '*.jpg' \) \
  2>/dev/null | sort > "$AUDIT_ROOT/inventory/likely_lineage_artifacts.txt"

# Hash likely source files. Missing paths are recorded rather than treated as fatal.
SOURCE_CANDIDATES=(
  "$REPO/src/foho/hand/hamer.py"
  "$REPO/third_party/estimator/hamer/hamer/models/hamer.py"
  "$REPO/third_party/estimator/hamer/hamer/models/mano_wrapper.py"
  "$REPO/third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py"
  "$REPO/third_party_patches/hy3dgen/shapegen/pipelines.py"
)
: > "$AUDIT_ROOT/inventory/source_hashes.sha256"
: > "$AUDIT_ROOT/inventory/source_hashes_missing.txt"
for p in "${SOURCE_CANDIDATES[@]}"; do
  if [[ -f "$p" ]]; then
    sha256sum "$p" >> "$AUDIT_ROOT/inventory/source_hashes.sha256"
  else
    echo "$p" >> "$AUDIT_ROOT/inventory/source_hashes_missing.txt"
  fi
done

cat > "$AUDIT_ROOT/decision/HOLD_CURRENT_STAGE.md" <<'MD'
# Current authorization state

Until the H0-H4 ladder passes under one coherent contract:

- target rewrite: **not authorized**
- guessed permutation: **not authorized**
- reflection: **not authorized**
- candidate scoring: **not authorized**
- mesh movement: **not authorized**
- MANO articulation: **not authorized**
- C2: **closed**
- F3.4: **closed**
- Gate D: **closed**
MD

log "[PASS] Gate-C state-equivalence audit workspace initialized"
log "AUDIT_ROOT=$AUDIT_ROOT"
log "Review next:"
log "  sed -n '1,320p' '$AUDIT_ROOT/inventory/keypoint_source_contract_hits.txt'"
log "  sed -n '1,320p' '$AUDIT_ROOT/inventory/likely_lineage_artifacts.txt'"
log "  \$EDITOR '$AUDIT_ROOT/manifests/state_ledger.csv'"
