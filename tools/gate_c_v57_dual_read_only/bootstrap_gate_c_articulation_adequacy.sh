#!/usr/bin/env bash
set -euo pipefail

: "${REPO:=/home/fredcui/Projects/FollowMyHold}"
: "${DATA:=/home/fredcui/foho_phase0}"
: "${CASE_ROOT:=$DATA/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2}"
: "${TOOL_ROOT:=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
: "${AUDIT_ROOT:=$CASE_ROOT/gate_c1_5_read_only_articulation_adequacy_v1}"

mkdir -p \
  "$AUDIT_ROOT"/{adapter,config,inventory,manifests,preflight,fd,analysis,decision,visuals,notes,preregistration}

copy_if_absent() {
  local src="$1" dst="$2"
  if [[ ! -e "$dst" ]]; then
    cp "$src" "$dst"
    echo "[CREATE] $dst"
  else
    echo "[KEEP]   $dst"
  fi
}

copy_if_absent "$TOOL_ROOT/templates/articulation_adequacy.env.template" "$AUDIT_ROOT/config/articulation_adequacy.env"
copy_if_absent "$TOOL_ROOT/templates/probe_config.json.template" "$AUDIT_ROOT/config/probe_config.json"
copy_if_absent "$TOOL_ROOT/config/articulation_adequacy_thresholds.json" "$AUDIT_ROOT/config/articulation_adequacy_thresholds.json"
copy_if_absent "$TOOL_ROOT/templates/parameter_manifest.csv" "$AUDIT_ROOT/manifests/parameter_manifest.csv"
copy_if_absent "$TOOL_ROOT/adapters/source_bound_adapter_TEMPLATE.py" "$AUDIT_ROOT/adapter/source_bound_adapter.py"

{
  echo "# Git state"
  date -Is
  git -C "$REPO" rev-parse HEAD 2>/dev/null || true
  git -C "$REPO" status --short 2>/dev/null || true
} > "$AUDIT_ROOT/inventory/git_state.txt"

if command -v rg >/dev/null 2>&1; then
  rg -n --hidden --glob '!*.git*' \
    'trans_hand|hand_pose|global_orient|mano.*forward|pred_keypoints_3d|mano_2d_kps|mano_3d_kps|mano_vert_to_3dkps|J_regressor|extra_joints|joint_map|axis_angle|aa_to_rotmat|batch_rodrigues' \
    "$REPO/src" "$REPO/scripts" "$REPO/tools" "$REPO/third_party" 2>/dev/null \
    > "$AUDIT_ROOT/inventory/source_pose_contract_hits.txt" || true
fi

find "$CASE_ROOT" -type f 2>/dev/null \
  \( -iname '*mano*' -o -iname '*hamer*' -o -iname '*kps*' -o -iname '*keypoint*' \
     -o -iname '*transform*' -o -iname '*camera*' -o -iname '*intrin*' \
     -o -iname '*branch*e*' -o -iname '*zero*update*' -o -iname '*candidate*' \) \
  -print | sort > "$AUDIT_ROOT/inventory/likely_probe_artifacts.txt" || true

find "$TOOL_ROOT" -type f -maxdepth 3 -print0 | sort -z | xargs -0 sha256sum \
  > "$AUDIT_ROOT/inventory/toolkit_hashes.sha256"

cat > "$AUDIT_ROOT/notes/NEXT.md" <<EOF
# Next

1. Review inventory/source_pose_contract_hits.txt and likely_probe_artifacts.txt.
2. Fill config/articulation_adequacy.env and source it.
3. Replace every REPLACE/TODO entry in manifests/parameter_manifest.csv.
4. Bind adapter/source_bound_adapter.py to the exact validated source forward.
5. Fill config/probe_config.json with exact source artifacts.
6. Run the positive-control/synthetic derivative calibration before v3.
7. Run preflight -> finite differences -> analysis -> decision.
8. Stop. Do not export a nonzero mesh or launch an optimizer from this toolkit.
EOF

echo "[READY] $AUDIT_ROOT"
echo "[NEXT]  $AUDIT_ROOT/notes/NEXT.md"
