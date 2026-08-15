#!/usr/bin/env bash
set -Eeuo pipefail

log() { printf '%s\n' "$*"; }
hold() { printf '[HOLD] %s\n' "$*" >&2; return 1; }

REPO="${REPO:-/home/fredcui/Projects/FollowMyHold}"
DATA="${DATA:-/home/fredcui/foho_phase0}"
CASE_ROOT="${CASE_ROOT:-$DATA/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2}"
AUDIT_ROOT="${AUDIT_ROOT:-$CASE_ROOT/gate_c_keypoint_lineage_v1}"
TOOL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

[[ -d "$REPO" ]] || { hold "FollowMyHold checkout not found: $REPO"; exit 1; }
[[ -d "$CASE_ROOT" ]] || { hold "Case root not found: $CASE_ROOT"; exit 1; }

mkdir -p \
  "$AUDIT_ROOT/inventory" \
  "$AUDIT_ROOT/contracts" \
  "$AUDIT_ROOT/reports" \
  "$AUDIT_ROOT/decision" \
  "$AUDIT_ROOT/manifests" \
  "$AUDIT_ROOT/preregistration"

cp -n "$TOOL_ROOT/config/lineage_thresholds.json" \
  "$AUDIT_ROOT/contracts/lineage_thresholds.json" 2>/dev/null || true
cp -n "$TOOL_ROOT/templates/artifact_manifest.csv" \
  "$AUDIT_ROOT/manifests/artifact_manifest.csv" 2>/dev/null || true
cp -n "$TOOL_ROOT/templates/preregistration_after_lineage.md" \
  "$AUDIT_ROOT/preregistration/preregistration_after_lineage.md" 2>/dev/null || true

{
  printf 'timestamp_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'repo=%s\n' "$REPO"
  printf 'case_root=%s\n' "$CASE_ROOT"
  printf 'audit_root=%s\n' "$AUDIT_ROOT"
  printf 'hostname=%s\n' "$(hostname)"
  printf 'python=%s\n' "$(python --version 2>&1 || true)"
  printf 'conda_env=%s\n' "${CONDA_DEFAULT_ENV:-unset}"
} > "$AUDIT_ROOT/inventory/runtime.txt"

(
  cd "$REPO"
  {
    git rev-parse HEAD 2>/dev/null || true
    git status --short 2>/dev/null || true
    git submodule status 2>/dev/null || true
  } > "$AUDIT_ROOT/inventory/git_state.txt"

  git diff -- \
    src/foho/hand/hamer.py \
    third_party/estimator/hamer/hamer/models/hamer.py \
    third_party/estimator/hamer/hamer/models/mano_wrapper.py \
    third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py \
    third_party_patches/hy3dgen/shapegen/pipelines.py \
    > "$AUDIT_ROOT/inventory/relevant_source_diff.patch" 2>/dev/null || true
)

SOURCE_CANDIDATES=(
  "$REPO/src/foho/hand/hamer.py"
  "$REPO/third_party/estimator/hamer/hamer/models/hamer.py"
  "$REPO/third_party/estimator/hamer/hamer/models/mano_wrapper.py"
  "$REPO/third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py"
  "$REPO/third_party_patches/hy3dgen/shapegen/pipelines.py"
)

: > "$AUDIT_ROOT/inventory/source_hashes.sha256"
for p in "${SOURCE_CANDIDATES[@]}"; do
  if [[ -f "$p" ]]; then
    sha256sum "$p" >> "$AUDIT_ROOT/inventory/source_hashes.sha256"
  fi
done

{
  for p in "${SOURCE_CANDIDATES[@]}"; do
    if [[ -f "$p" ]]; then
      printf '\n===== %s =====\n' "$p"
      rg -n -C 4 \
        'pred_keypoints_3d|pred_vertices|mano_output\.joints|J_regressor|extra_joints_idxs|joint_map|mano_to_openpose|FINGERTIP|mano_vert_to_3dkps|kps_for_guidance|pred_kps_3d_proj|right_flag|multiplier' \
        "$p" || true
    fi
  done
} > "$AUDIT_ROOT/inventory/keypoint_source_contract_hits.txt"

find "$REPO" "$CASE_ROOT" -type f \
  \( -name '*.npy' -o -name '*.npz' -o -name '*.pt' -o -name '*.pth' \
     -o -name '*.obj' -o -name '*.ply' -o -name '*.glb' -o -name '*.json' \
     -o -name '*.csv' \) \
  2>/dev/null | sort > "$AUDIT_ROOT/inventory/all_candidate_artifacts.txt"

rg -i \
  'hamer|mano|keypoint|kps|guidance|aligned.*hand|hand.*aligned|candidate|camera|intrinsic|projection|c1|branch.?e' \
  "$AUDIT_ROOT/inventory/all_candidate_artifacts.txt" \
  > "$AUDIT_ROOT/inventory/likely_lineage_artifacts.txt" || true

{
  printf 'Expected stage contract:\n'
  printf 'H0 raw vertices -> raw pred_keypoints_3d\n'
  printf 'H1 handedness-adjusted joints -> guidance 3D joints\n'
  printf 'H2 guidance 3D joints -> guidance 2D projection\n'
  printf 'H3 source joints through C1/shared frame\n'
  printf 'H4 live helper from exact zero-update mesh\n\n'
  printf 'No optimizer, mesh movement, C2, F3.4, or Gate D is authorized by this bootstrap.\n'
} > "$AUDIT_ROOT/inventory/audit_scope.txt"

log "[PASS] Read-only Gate-C lineage audit initialized"
log "AUDIT_ROOT=$AUDIT_ROOT"
log "Review next:"
log "  sed -n '1,260p' '$AUDIT_ROOT/inventory/keypoint_source_contract_hits.txt'"
log "  sed -n '1,260p' '$AUDIT_ROOT/inventory/likely_lineage_artifacts.txt'"
log "  \$EDITOR '$AUDIT_ROOT/manifests/artifact_manifest.csv'"
