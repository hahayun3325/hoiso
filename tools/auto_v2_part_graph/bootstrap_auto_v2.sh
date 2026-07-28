#!/usr/bin/env bash
# Professor-approved AUTO-V2 bootstrap for alapuse02v3n60.
# Creates a fixed method-level branch, prompts, schemas, and path inventories.
# It does not run a VLM, SAM2, Hunyuan, or overwrite existing results.
# It intentionally avoids `exit 2` and Python `SystemExit(2)`.

PROJECT_ROOT="/home/fredcui/Projects/FollowMyHold"
CONDA_SH="/home/fredcui/anaconda3/etc/profile.d/conda.sh"
CASE_ID="alapuse02v3n60"
V3N60_ROOT="/home/fredcui/foho_phase0/vlm_failure_containment/$CASE_ID"
FALLBACK_ROOT="$V3N60_ROOT/inpainting_fallback"
CANDIDATE_ROOT="$FALLBACK_ROOT/candidates"
REPAIR_G="$CANDIDATE_ROOT/repair_G_mask_union_hole_filled"
REPAIR_I="$CANDIDATE_ROOT/repair_I_reviewed_full_lid_silhouette"
REPAIR_J="$CANDIDATE_ROOT/repair_J_auto_target_resegment"
REPAIR_K="$CANDIDATE_ROOT/repair_K_auto_distractor_separation"
AUTO_V2="$FALLBACK_ROOT/automatic_recovery_v2_part_graph"

if test -d "$PROJECT_ROOT"; then
  cd "$PROJECT_ROOT" || echo "[HOLD] PROJECT_CD_FAILED=$PROJECT_ROOT"
else
  echo "[HOLD] PROJECT_ROOT_MISSING=$PROJECT_ROOT"
fi

if test -f "$CONDA_SH"; then
  # shellcheck source=/dev/null
  source "$CONDA_SH"
  conda activate foho || echo "[HOLD] CONDA_ACTIVATE_FAILED=foho"
else
  echo "[HOLD] CONDA_SH_MISSING=$CONDA_SH"
fi

mkdir -p \
  "$AUTO_V2/preregistration" \
  "$AUTO_V2/source" \
  "$AUTO_V2/vlm_spatial" \
  "$AUTO_V2/part_masks" \
  "$AUTO_V2/candidate_bank" \
  "$AUTO_V2/vlm_critic" \
  "$AUTO_V2/selection" \
  "$AUTO_V2/auth" \
  "$AUTO_V2/hunyuan" \
  "$AUTO_V2/evaluation" \
  "$AUTO_V2/review"

PREREG="$AUTO_V2/preregistration/auto_v2_preregistration.json"
if test -e "$PREREG"; then
  echo "[HOLD] AUTO_V2_PREREG_ALREADY_EXISTS=$PREREG"
else
  cat > "$PREREG" <<'EOF'
{
  "schema_version": "auto_recovery_v2_preregistration_v1",
  "case_id": "alapuse02v3n60",
  "method_id": "part_graph_spatial_grounding_plus_vlm_rejection",
  "development_case": true,
  "automatic_success_claim_requires_held_out_replication": true,
  "candidate_I_role": "evaluation_oracle_only",
  "candidate_I_pixels_coordinates_or_mesh_may_be_used_for_generation": false,
  "v6n60_allowed_use": "semantic_part_schema_only",
  "v6n60_pixels_coordinates_masks_or_mesh_may_be_used": false,
  "fixed_region_labels": [
    "whole_laptop",
    "laptop_lid",
    "laptop_base",
    "wooden_support",
    "tabletop"
  ],
  "fixed_candidate_ids": [
    "c01_whole_minus_distractors",
    "c02_part_union_raw",
    "c03_part_union_minus_distractors",
    "c04_part_graph_complete"
  ],
  "maximum_spatial_proposals": 1,
  "maximum_sam2_configurations": 1,
  "maximum_candidate_bank_size": 4,
  "maximum_blind_critic_queries": 1,
  "maximum_hunyuan_runs": 1,
  "hunyuan_settings": {
    "steps": 30,
    "octree_resolution": 384,
    "num_chunks": 8000,
    "seed": 1234
  },
  "pre_hunyuan_gate": {
    "critic_confidence_min": 0.80,
    "support_overlap_fraction_max": 0.005,
    "tabletop_overlap_fraction_max": 0.005,
    "bottom_border_touch_fraction_max": 0.02,
    "largest_component_fraction_min": 0.85,
    "max_components": 3,
    "lid_retention_min": 0.90,
    "base_retention_min": 0.90
  },
  "forbidden": [
    "manual_roi_or_polygon_in_automatic_branch",
    "editing_raw_vlm_response",
    "using_candidate_I_geometry_to_build_candidates",
    "using_v6n60_pixels_or_geometry_to_build_candidates",
    "prompt_synonym_search_after_viewing_results",
    "running_hunyuan_after_any_hold",
    "creating_an_unregistered_fifth_candidate"
  ],
  "stop_rule": "If no fixed candidate passes deterministic plus blind VLM gates, record AUTO_V2 failure and freeze further tuning on v3n60."
}
EOF
  echo "[PASS] AUTO_V2_PREREG_WRITTEN=$PREREG"
fi

find "$FALLBACK_ROOT" -type f \( \
  -name '01_reference_crop.png' -o \
  -name 'contextual_inpaint.png' -o \
  -name 'repaired_object_mask.png' -o \
  -name 'hunyuan_input_rgb.png' -o \
  -name 'positive_only_square_hunyuan_ready.png' \
\) 2>/dev/null | sort > "$AUTO_V2/source/source_inventory.txt"

echo "[INFO] AUTO_V2_SOURCE_INVENTORY=$AUTO_V2/source/source_inventory.txt"

cat > "$AUTO_V2/source/paths.env.template" <<EOF
export CASE_ID='$CASE_ID'
export AUTO_V2='$AUTO_V2'
export REFERENCE_RGB='$REPAIR_I/01_reference_crop.png'
export CONTEXT_RGB='$REPAIR_G/contextual_inpaint.png'
export OPTIONAL_WHOLE_MASK='$REPAIR_J/repaired_object_mask.png'
export ORACLE_MASK_EVAL_ONLY='$REPAIR_I/02_object_mask.png'
export SAM2_CONFIG='REPLACE_WITH_INSTALLED_SAM2_CONFIG_IDENTIFIER'
export SAM2_CHECKPOINT='REPLACE_WITH_INSTALLED_SAM2_CHECKPOINT_PATH'
EOF

echo "[PASS] AUTO_V2_PATH_TEMPLATE=$AUTO_V2/source/paths.env.template"

cat > "$AUTO_V2/review/code_capability_inventory.sh" <<'EOF'
#!/usr/bin/env bash
cd /home/fredcui/Projects/FollowMyHold || echo '[HOLD] PROJECT_CD_FAILED'
rg -n -i -C 3 \
  'SAM2ImagePredictor|build_sam2|box.*prompt|LangSAM|GroundingDINO|run_hunyuan_shape_dryrun|guard_vlm_inpaint_response|validate_vlm_inpaint_asset' \
  scripts src tools third_party 2>/dev/null \
  | tee /home/fredcui/foho_phase0/vlm_failure_containment/alapuse02v3n60/inpainting_fallback/automatic_recovery_v2_part_graph/review/code_capability_inventory.txt
find /home/fredcui/Projects -type f \( -name 'sam2*.yaml' -o -name 'sam2.1*.yaml' -o -name 'sam2*.pt' \) 2>/dev/null \
  | sort \
  | tee /home/fredcui/foho_phase0/vlm_failure_containment/alapuse02v3n60/inpainting_fallback/automatic_recovery_v2_part_graph/review/sam2_asset_inventory.txt
EOF
chmod +x "$AUTO_V2/review/code_capability_inventory.sh"

echo "[PASS] AUTO_V2_CODE_INVENTORY_COMMAND=$AUTO_V2/review/code_capability_inventory.sh"
echo "[NEXT] Copy the toolkit Python files and prompt templates into AUTO_V2 or scripts/phase2_1."
echo "[NEXT] Confirm REFERENCE_RGB and CONTEXT_RGB from source_inventory.txt."
echo "[NEXT] Run one exact-schema spatial proposal, then box-prompted SAM2, fixed candidate-bank construction, one blind critic, existing provenance guard, and one fixed-seed Hunyuan run."
