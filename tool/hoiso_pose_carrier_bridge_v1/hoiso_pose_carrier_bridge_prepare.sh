#!/usr/bin/env bash
set -u

PROJECT_ROOT="${PROJECT_ROOT:-/home/fredcui/Projects/FollowMyHold}"
OFFICIAL_ROOT="${OFFICIAL_ROOT:-/home/fredcui/Projects/hoi_related_work_inspection/FollowMyHold}"
DATA_ROOT="${DATA_ROOT:-/home/fredcui/foho_phase0}"
CASE="${CASE:-alapuse02v3n60_auto_v2}"
CASE_ROOT="${CASE_ROOT:-$DATA_ROOT/phase2_gateA_part_recon/cases/$CASE}"
CARRIER_ROOT="${CARRIER_ROOT:-$CASE_ROOT/gate_c_pose_carrier}"

mkdir -p \
  "$CARRIER_ROOT/input" \
  "$CARRIER_ROOT/carrier" \
  "$CARRIER_ROOT/h2m" \
  "$CARRIER_ROOT/support_review" \
  "$CARRIER_ROOT/gateA_to_carrier" \
  "$CARRIER_ROOT/composed_zero_step" \
  "$CARRIER_ROOT/receipts" \
  "$CARRIER_ROOT/visuals" \
  "$CARRIER_ROOT/hashes"

printf '[INFO] PROJECT_ROOT=%s\n' "$PROJECT_ROOT"
printf '[INFO] OFFICIAL_ROOT=%s\n' "$OFFICIAL_ROOT"
printf '[INFO] CASE_ROOT=%s\n' "$CASE_ROOT"
printf '[INFO] CARRIER_ROOT=%s\n' "$CARRIER_ROOT"

check_path() {
  local p="$1"
  if [[ -e "$p" ]]; then
    printf '[PASS] PATH=%s\n' "$p"
  else
    printf '[HOLD] MISSING=%s\n' "$p"
  fi
}

check_path "$PROJECT_ROOT"
check_path "$OFFICIAL_ROOT"
check_path "$CASE_ROOT"

{
  printf 'PROJECT_ROOT=%s\n' "$PROJECT_ROOT"
  printf 'OFFICIAL_ROOT=%s\n' "$OFFICIAL_ROOT"
  printf 'CASE_ROOT=%s\n' "$CASE_ROOT"
  printf 'CARRIER_ROOT=%s\n' "$CARRIER_ROOT"
} > "$CARRIER_ROOT/receipts/bootstrap_paths.env"

for repo in "$PROJECT_ROOT" "$OFFICIAL_ROOT"; do
  if git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    name="$(basename "$repo")"
    {
      printf 'repo=%s\n' "$repo"
      printf 'branch=%s\n' "$(git -C "$repo" branch --show-current 2>/dev/null || true)"
      printf 'commit=%s\n' "$(git -C "$repo" rev-parse HEAD 2>/dev/null || true)"
      printf '%s\n' '--- status --short ---'
      git -C "$repo" status --short 2>/dev/null || true
    } > "$CARRIER_ROOT/receipts/${name}_git_state.txt"
  fi
done

# Inventory likely accepted Gate-A assets without assuming one exact historical name.
find "$CASE_ROOT" -type f \
  \( -iname '*gate*a*fixed*object*.ply' \
     -o -iname '*laptop*mesh*fixed*.ply' \
     -o -iname '*screen*lid*.ply' \
     -o -iname '*keyboard*base*.ply' \
     -o -iname '*gate*a*provenance*.json' \
     -o -iname '*accepted*object*.json' \) \
  -print | sort \
  > "$CARRIER_ROOT/receipts/gatea_asset_inventory.txt"

# Inventory clean-input previews and masks.
find "$CASE_ROOT" -type f \
  \( -iname '*clean*hoi*.png' \
     -o -iname '*clean*hoi*.jpg' \
     -o -iname '*clean*hoi*.json' \
     -o -iname '*object*mask*.png' \
     -o -iname '*obj*mask*.png' \
     -o -iname '*hand*mask*.png' \
     -o -iname '*guard*mask*.png' \) \
  -print | sort \
  > "$CARRIER_ROOT/receipts/clean_input_inventory.txt"

# Recover the official Hunyuan-to-MoGe / ICP implementation.
if command -v rg >/dev/null 2>&1; then
  rg -n -i \
    'transform_hunyuan2moge|h2m_transformations|hunyuan_hoi_out|iterative.closest|registration_icp|ICP|umeyama|similarity|centroid|global.scale' \
    "$OFFICIAL_ROOT" \
    "$PROJECT_ROOT/src" \
    "$PROJECT_ROOT/scripts" \
    "$PROJECT_ROOT/third_party" \
    -g '*.py' -g '*.sh' \
    > "$CARRIER_ROOT/receipts/official_hunyuan_to_moge_source_trace.txt" 2>&1 || true

  # Recover the project-owned coarse-HOI generation entry point and prior receipts.
  rg -n -i \
    'hunyuan_hoi_out|Hunyuan3D|hoi_mesh|generate.*hoi|seed|save.*hoi|Hunyuan3DDiTFlowMatchingPipeline' \
    "$PROJECT_ROOT/scripts" \
    "$PROJECT_ROOT/src" \
    "$PROJECT_ROOT/third_party" \
    -g '*.py' -g '*.sh' \
    > "$CARRIER_ROOT/receipts/hunyuan_carrier_generation_source_trace.txt" 2>&1 || true

  rg -n -i \
    'alapuse02v3|hunyuan|hoi_mesh|hunyuan_hoi_out' \
    "$CASE_ROOT" "$DATA_ROOT/phase1_diagnostics" \
    -g '*.json' -g '*.txt' -g '*.log' \
    > "$CARRIER_ROOT/receipts/historical_carrier_receipt_trace.txt" 2>&1 || true
else
  printf '[HOLD] rg is not installed; source traces were not generated.\n'
fi

find "$DATA_ROOT" -type f \
  \( -iname '*command*.json' \
     -o -iname '*launch*.json' \
     -o -iname '*receipt*.json' \
     -o -iname '*started*.json' \) \
  -printf '%T@ %p\n' 2>/dev/null \
  | sort -n | tail -150 \
  > "$CARRIER_ROOT/receipts/recent_launch_receipts.txt"

cat > "$CARRIER_ROOT/input/input_review.template.json" <<'JSON'
{
  "schema": "hoiso_clean_pose_carrier_input_review_v1",
  "case_id": "alapuse02v3n60_auto_v2",
  "rgb_path": null,
  "object_mask_path": null,
  "modeled_upper_hand_mask_path": null,
  "unmodeled_lower_hand_guard_path": null,
  "same_raster_confirmed": false,
  "relative_pixels_unchanged": false,
  "stand_background_excluded": false,
  "lower_hand_excluded_from_object_support": false,
  "lower_hand_excluded_from_hunyuan_union_or_explicitly_ignored": false,
  "decision": "review_required",
  "authorizes_one_pinned_carrier_generation": false
}
JSON

cat > "$CARRIER_ROOT/carrier/carrier_launch_contract.template.json" <<'JSON'
{
  "schema": "hoiso_pinned_hunyuan_hoi_pose_carrier_launch_v1",
  "purpose": "POSE_CARRIER_ONLY_NOT_FINAL_OBJECT",
  "input_rgb_or_rgba": null,
  "object_mask": null,
  "modeled_hand_mask": null,
  "ignore_or_guard_mask": null,
  "model_checkpoint": null,
  "seed": null,
  "inference_settings": null,
  "project_commit": null,
  "entry_point": null,
  "literal_command": null,
  "fresh_output_root": null,
  "object_optimization_enabled": false,
  "joint_optimization_enabled": false,
  "authorizes_gpu_execution": false
}
JSON

cat > "$CARRIER_ROOT/h2m/h2m_contract.template.json" <<'JSON'
{
  "schema": "hoiso_fresh_carrier_to_moge_contract_v1",
  "carrier_path": null,
  "carrier_sha256": null,
  "moge_target_path": null,
  "moge_target_sha256": null,
  "crop_image_identifier": null,
  "camera_fov_source": null,
  "official_source_file_and_lines": [],
  "official_commit": null,
  "literal_command": null,
  "matrix_output": null,
  "final_transform_type": null,
  "row_or_column_convention": null,
  "authorizes_execution": false
}
JSON

cat > "$CARRIER_ROOT/gateA_to_carrier/fit_contract.template.json" <<'JSON'
{
  "schema": "hoiso_gatea_to_hunyuan_carrier_fit_v1",
  "gatea_whole_mesh": null,
  "gatea_lid_mesh": null,
  "gatea_base_mesh": null,
  "carrier_object_support": null,
  "support_provenance": null,
  "transform_family": "proper_shared_root_sim3",
  "uniform_scale_only": true,
  "proper_rotation_only": true,
  "reflection_allowed": false,
  "per_part_scale_allowed": false,
  "hinge_correction_active": false,
  "candidate_scoring": [
    "trimmed_bidirectional_surface_distance",
    "object_silhouette",
    "depth_ordering",
    "lid_support",
    "base_support",
    "lid_base_orientation"
  ],
  "authorizes_fit": false
}
JSON

printf '[PASS] PREPARATION_COMPLETE=%s\n' "$CARRIER_ROOT"
printf '[HOLD] No mask edit, Hunyuan generation, H2M fit, Gate-A fit, or GPU optimization was executed.\n'
