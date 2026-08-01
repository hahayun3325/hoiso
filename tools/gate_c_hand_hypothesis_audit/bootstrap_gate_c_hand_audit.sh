#!/usr/bin/env bash
# Safe bootstrap for the alapuse02v3n60 Gate-C hand identity/correspondence audit.
# This script does not run HaMeR, Hunyuan, an optimizer, C2, F3.4, or Gate D.

set -u
set -o pipefail

TOOLKIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-/home/fredcui/Projects/FollowMyHold}"
DATA="${DATA:-/home/fredcui/foho_phase0}"
CASE_ROOT="${CASE_ROOT:-$DATA/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2}"
V3_RUN="${V3_RUN:-$DATA/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse02_v3_selector_v41_refined_pipeline}"
AUDIT_ROOT="${AUDIT_ROOT:-$CASE_ROOT/gate_c0_hand_identity_correspondence_audit_v1}"

mkdir -p \
  "$AUDIT_ROOT/inventory" \
  "$AUDIT_ROOT/manifests" \
  "$AUDIT_ROOT/config" \
  "$AUDIT_ROOT/reports" \
  "$AUDIT_ROOT/vlm" \
  "$AUDIT_ROOT/decisions" \
  "$AUDIT_ROOT/logs"

copy_once() {
  local src="$1"
  local dst="$2"
  if [[ -f "$dst" ]]; then
    printf '[INFO] KEEP_EXISTING=%s\n' "$dst"
  elif [[ -f "$src" ]]; then
    cp "$src" "$dst"
    printf '[PASS] TEMPLATE_COPIED=%s\n' "$dst"
  else
    printf '[HOLD] TEMPLATE_SOURCE_MISSING=%s\n' "$src"
  fi
}

copy_once "$TOOLKIT_DIR/templates/hand_candidates.template.csv" \
  "$AUDIT_ROOT/manifests/hand_candidates.csv"
copy_once "$TOOLKIT_DIR/templates/keypoint_mapping.identity_21.template.json" \
  "$AUDIT_ROOT/config/keypoint_mapping.json"
copy_once "$TOOLKIT_DIR/templates/raster_affine.identity.template.json" \
  "$AUDIT_ROOT/config/raster_affine.json"
copy_once "$TOOLKIT_DIR/templates/thresholds.template.json" \
  "$AUDIT_ROOT/config/thresholds.json"
copy_once "$TOOLKIT_DIR/templates/vlm_hand_choice_prompt.md" \
  "$AUDIT_ROOT/vlm/vlm_hand_choice_prompt.md"
copy_once "$TOOLKIT_DIR/templates/vlm_hand_choice.schema.json" \
  "$AUDIT_ROOT/vlm/vlm_hand_choice.schema.json"

INVENTORY="$AUDIT_ROOT/inventory/hand_candidate_files.txt"
: > "$INVENTORY"
for root in "$V3_RUN" "$CASE_ROOT" "$DATA"; do
  if [[ -d "$root" ]]; then
    find "$root" -type f \
      \( -iname '*mano*.ply' \
         -o -iname '*mano*.npz' \
         -o -iname '*mano*.pkl' \
         -o -iname '*hand*.ply' \
         -o -iname '*hand*.obj' \
         -o -iname '*kps*.npy' \
         -o -iname '*keypoint*.npy' \
         -o -iname '*joint*.npy' \
         -o -iname '*camera*.json' \
         -o -iname '*camera*.npz' \
         -o -iname '*intrinsic*.npy' \
         -o -iname '*crop*.json' \
         -o -iname '*bbox*.json' \) \
      2>/dev/null
  else
    printf '[HOLD] SEARCH_ROOT_MISSING=%s\n' "$root" >&2
  fi
done | sort -u > "$INVENTORY"
printf '[PASS] HAND_FILE_INVENTORY=%s\n' "$INVENTORY"
printf '[INFO] HAND_FILE_COUNT=%s\n' "$(wc -l < "$INVENTORY" | tr -d ' ')"

CODE_AUDIT="$AUDIT_ROOT/inventory/source_code_provenance_hits.txt"
: > "$CODE_AUDIT"
if [[ -d "$REPO" ]]; then
  (
    cd "$REPO" || return 0
    rg -n --hidden --glob '!*.git*' \
      'pred_keypoints|keypoints_2d|mano|handed|right_hand|left_hand|crop.*transform|bbox.*transform|horizontal.*flip|flip.*crop|project.*joint' \
      src scripts third_party configs 2>/dev/null | head -n 2000
  ) > "$CODE_AUDIT"
  printf '[PASS] SOURCE_CODE_AUDIT_HITS=%s\n' "$CODE_AUDIT"
else
  printf '[HOLD] REPO_MISSING=%s\n' "$REPO"
fi

CONTEXT="$AUDIT_ROOT/audit_context.json"
python3 - "$REPO" "$DATA" "$CASE_ROOT" "$V3_RUN" "$AUDIT_ROOT" "$INVENTORY" "$CONTEXT" <<'PY'
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

repo, data, case_root, v3_run, audit_root, inventory, output = map(Path, sys.argv[1:])

def bind(path: Path):
    if not path.is_file():
        return {"path": str(path), "missing": True}
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    }

record = {
    "schema_version": "gate_c_hand_identity_audit_context_v1",
    "case_id": "alapuse02v3n60",
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
    "paths": {
        "repo": str(repo),
        "data": str(data),
        "case_root": str(case_root),
        "v3_run": str(v3_run),
        "audit_root": str(audit_root),
    },
    "inventory": bind(inventory),
    "frozen_decisions": {
        "branch_e_translation_only": "closed",
        "root_rotation_only": "closed",
        "reflection_only": "closed",
        "object_geometry": "fixed_for_hand_hypothesis_audit",
        "lid_base_relative_transform": "fixed",
    },
    "authorizations": {
        "run_new_optimizer": False,
        "run_c2": False,
        "run_f34": False,
        "run_gate_d": False,
    },
    "required_manual_resolutions": [
        "target RGB path",
        "frozen upper-hand target keypoint path and exact joint order",
        "candidate projected keypoint paths in a documented raster",
        "candidate physical hand identity and handedness",
        "source-proven keypoint mapping",
        "source-proven raster affine/crop transform",
        "positive-reference threshold calibration on alapuse02v6n60",
    ],
}
output.write_text(json.dumps(record, indent=2) + "\n")
print(f"[PASS] AUDIT_CONTEXT={output}")
PY

cat > "$AUDIT_ROOT/paths_to_resolve.txt" <<'TXT'
Resolve these paths before running the deterministic audit:

TARGET_RGB=/absolute/path/to/the/exact_target_crop.png
TARGET_KPS=/absolute/path/to/frozen_upper_hand_target_keypoints.npy
TARGET_HAND_MASK=/absolute/path/to/target_upper_hand_mask.png   # optional

For every candidate, fill manifests/hand_candidates.csv with:
- exact projected keypoints in the target raster,
- source frame,
- physical upper/lower hand identity,
- handedness,
- whether the crop was mirrored,
- exact semantic joint order,
- exact crop/raster affine,
- optional hand mesh and mask.

Do not mark a field "verified" from visual intuition alone. Trace the producer code,
metadata, crop box, and joint-order definition.
TXT
printf '[PASS] PATH_CHECKLIST=%s\n' "$AUDIT_ROOT/paths_to_resolve.txt"

printf '\n[READY] AUDIT_ROOT=%s\n' "$AUDIT_ROOT"
printf '[NEXT] Inspect inventory and source-code hits, then edit the manifest/config files.\n'
printf '[HOLD] No optimizer has been authorized or launched.\n'
