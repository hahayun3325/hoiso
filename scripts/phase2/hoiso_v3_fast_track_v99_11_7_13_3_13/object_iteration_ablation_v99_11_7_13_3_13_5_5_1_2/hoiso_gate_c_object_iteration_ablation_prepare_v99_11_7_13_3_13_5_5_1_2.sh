#!/usr/bin/env bash

main() {
set -euo pipefail

# Preparation-only helper for the alapuse02v3n60 object-only iteration ablation.
# It does not launch Hunyuan, modify source, or run a GPU workload.

PROJECT_ROOT="${PROJECT_ROOT:-/home/fredcui/Projects/FollowMyHold}"
DATA_ROOT="${DATA_ROOT:-/home/fredcui/foho_phase0}"
CASE_NAME="${CASE_NAME:-alapuse02v3n60_auto_v2}"
CASE_ROOT="${CASE_ROOT:-$DATA_ROOT/phase2_gateA_part_recon/cases/$CASE_NAME}"
RENDER_NAME="${RENDER_NAME:-s100_up_post_object_before_joint_flow_v99_11_7_13_3_13_5_2_2_5_4_3_1.png}"
PIPELINE_SOURCE="${PIPELINE_SOURCE:-$PROJECT_ROOT/third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines_v99_11_7_13_3_13.py}"
GUIDANCE_CALLER="${GUIDANCE_CALLER:-$PROJECT_ROOT/src/foho/guidance/run.py}"
OUTER_LAUNCHER="${OUTER_LAUNCHER:-$PROJECT_ROOT/scripts/phase1/run_selector_v41_full_pipeline_one.sh}"

for path in "$PROJECT_ROOT" "$CASE_ROOT"; do
  if [[ ! -d "$path" ]]; then
    echo "[HOLD] MISSING_DIRECTORY=$path" >&2
    return 2
  fi
done

mapfile -t render_matches < <(find "$CASE_ROOT" -type f -name "$RENDER_NAME" -print | sort)
if [[ ${#render_matches[@]} -ne 1 ]]; then
  echo "[HOLD] RENDER_MATCH_COUNT=${#render_matches[@]} NAME=$RENDER_NAME" >&2
  printf '%s\n' "${render_matches[@]:-}" >&2
  return 2
fi

BEFORE_JOINT_RENDER="${render_matches[0]}"
CURRENT_RUN_DIR="$(dirname "$BEFORE_JOINT_RENDER")"
STAMP="$(date +%Y%m%d_%H%M%S)"
ABL_ROOT="$CASE_ROOT/gate_c_object_only_iteration_ablation/$STAMP"
mkdir -p "$ABL_ROOT"/{config,evidence,hashes,launch,metrics,renders,notes}

printf '%s\n' "$BEFORE_JOINT_RENDER" > "$ABL_ROOT/evidence/baseline_render_path.txt"
printf '%s\n' "$CURRENT_RUN_DIR" > "$ABL_ROOT/evidence/current_run_dir.txt"

if git -C "$PROJECT_ROOT" rev-parse HEAD >/dev/null 2>&1; then
  git -C "$PROJECT_ROOT" rev-parse HEAD > "$ABL_ROOT/evidence/repo_commit.txt"
  git -C "$PROJECT_ROOT" status --short > "$ABL_ROOT/evidence/git_status_short.txt"
fi

if command -v conda >/dev/null 2>&1; then
  conda env export --no-builds > "$ABL_ROOT/evidence/foho_environment.yml" 2>/dev/null || true
fi

find "$CURRENT_RUN_DIR" -maxdepth 4 -type f \
  \( -iname '*.ply' -o -iname '*.obj' -o -iname '*.glb' -o -iname '*.npz' \
     -o -iname '*.npy' -o -iname '*.json' -o -iname '*.png' -o -iname '*.log' \
     -o -iname '*.txt' \) -print | sort \
  > "$ABL_ROOT/evidence/current_run_file_inventory.txt"

find "$CASE_ROOT" -type f \
  \( -iname '*command*.json' -o -iname '*receipt*.json' -o -iname '*launch*.json' \
     -o -iname '*started*.json' \) -printf '%T@ %p\n' | sort -n | tail -120 \
  > "$ABL_ROOT/evidence/recent_command_receipts.txt"

{
  echo '=== PIPELINE SOURCE HITS ==='
  if [[ -f "$PIPELINE_SOURCE" ]]; then
    rg -n -C 8 \
      'phase[[:space:]]*=[[:space:]]*1\.5|phase[[:space:]]*==[[:space:]]*1\.5|object.?only|scale_obj|trans_obj|rotation_obj|optimization_steps_scale|noise_obj_lr|num.*iter|range\(|early.?stop|scheduler\.step|noise_pred_obj' \
      "$PIPELINE_SOURCE" || true
  else
    echo "[HOLD] PIPELINE_SOURCE_MISSING=$PIPELINE_SOURCE"
  fi
  echo
  echo '=== CALLER HITS ==='
  for source in "$GUIDANCE_CALLER" "$OUTER_LAUNCHER"; do
    if [[ -f "$source" ]]; then
      echo "--- $source ---"
      rg -n -C 6 \
        'object.?only|phase|iter|step|optimization_steps_scale|noise_obj_lr|output|save_path|already exists, skipping' \
        "$source" || true
    else
      echo "[HOLD] SOURCE_MISSING=$source"
    fi
  done
} > "$ABL_ROOT/evidence/object_only_source_trace.txt"

find "$PROJECT_ROOT/configs" "$CASE_ROOT" -type f 2>/dev/null \
  \( -iname '*alapuse02v3n60*' -o -iname '*alapuse02_v3*' \) -print | sort \
  > "$ABL_ROOT/evidence/candidate_config_files.txt" || true

cat > "$ABL_ROOT/config/ablation_scope.json" <<JSON
{
  "schema": "gate_c_object_only_iteration_ablation_v1",
  "case": "$CASE_NAME",
  "baseline_render": "$BEFORE_JOINT_RENDER",
  "question": "under_convergence_vs_scale_translation_or_frame_mismatch",
  "fixed": [
    "accepted_articulated_object",
    "screen_lid_keyboard_base_shared_root",
    "hinge_state",
    "frozen_s100_up_hand",
    "camera_and_target_maps",
    "random_seed",
    "learning_rates",
    "active_losses",
    "optimizer_type"
  ],
  "only_planned_change": "verified_object_only_iteration_budget",
  "required_budgets": ["N", "2N", "4N"],
  "required_checkpoints": ["0", "0.25N", "0.5N", "N", "1.5N", "2N", "3N", "4N"],
  "contact_loss_active": false,
  "collision_loss_active": false,
  "joint_flow_active": false,
  "authorizes_gpu_execution": false
}
JSON

cat > "$ABL_ROOT/launch/launch_matrix.template.tsv" <<'TSV'
label	object_only_budget	config_or_command	output_root	status
baseline_N	REPLACE_N	REPLACE_EXACT_SOURCE_BOUND_COMMAND	REPLACE_UNIQUE_OUTPUT_ROOT	HOLD
extended_2N	REPLACE_2N	REPLACE_EXACT_SOURCE_BOUND_COMMAND	REPLACE_UNIQUE_OUTPUT_ROOT	HOLD
extended_4N	REPLACE_4N	REPLACE_EXACT_SOURCE_BOUND_COMMAND	REPLACE_UNIQUE_OUTPUT_ROOT	HOLD
TSV

cat > "$ABL_ROOT/config/checkpoint_metric_schema.json" <<'JSON'
{
  "optimization_variables": [
    "object_scale",
    "object_translation_xyz",
    "object_translation_norm",
    "object_rotation",
    "parameter_delta_since_previous_checkpoint"
  ],
  "losses": [
    "total",
    "normal",
    "depth_or_disparity",
    "silhouette",
    "regularization"
  ],
  "image_metrics": [
    "silhouette_iou",
    "depth_residual",
    "normal_residual"
  ],
  "object_metrics": [
    "bbox_extents",
    "bbox_diagonal",
    "center",
    "largest_component_fraction"
  ],
  "hand_relative_observation_only": [
    "hand_to_object_min",
    "hand_to_object_p5",
    "hand_to_object_mean",
    "object_minus_hand_center",
    "center_distance",
    "fingertip_to_screen_lid_distance",
    "penetration_or_inside_count_when_valid"
  ]
}
JSON

# Hash only small and directly relevant evidence here. Large model weights are intentionally excluded.
{
  sha256sum "$BEFORE_JOINT_RENDER"
  for source in "$PIPELINE_SOURCE" "$GUIDANCE_CALLER" "$OUTER_LAUNCHER"; do
    [[ -f "$source" ]] && sha256sum "$source"
  done
} > "$ABL_ROOT/hashes/preparation_inputs.sha256"

cat > "$ABL_ROOT/notes/NEXT.md" <<EOF
# Preparation result

The object-only iteration ablation is not yet authorized.

Before launch, resolve and record:

1. the exact object-only iteration variable and its current value N;
2. whether scale, xyz translation, rotation, and noise/geometry are active;
3. all learning rates and active loss terms;
4. whether the hand is exactly frozen;
5. whether the accepted object is mesh-only or latent-backed;
6. a step-0 state showing the accepted object and frozen hand in the intended shared frame;
7. three literal commands or one single 4N command with N/2N/4N checkpoints;
8. unique no-clobber output roots;
9. v6-calibrated joint-stage capture envelope.

Prefer one fresh deterministic 4N execution with checkpoints at N, 2N, and 4N over three unrelated executions.
EOF

printf '[PASS] PREPARATION_ONLY_ROOT=%s\n' "$ABL_ROOT"
printf '[HOLD] GPU_EXECUTION_NOT_AUTHORIZED\n'
}

main "$@"
