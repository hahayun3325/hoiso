#!/usr/bin/env bash
# Preparation-only audit for the HOISO-Flow object-only -> joint-flow fast track.
# This script performs no GPU model loading, no optimization, and no file overwrite.
set -u -o pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/home/fredcui/Projects/FollowMyHold}"
DATA_ROOT="${DATA_ROOT:-/home/fredcui/foho_phase0}"
CASE_ROOT="${CASE_ROOT:-$DATA_ROOT/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2}"
HAND_ROOT="${HAND_ROOT:-$CASE_ROOT/gate_c_hand_anchor}"

PIPE_PARENT="${PIPE_PARENT:-$PROJECT_ROOT/third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py}"
GUIDANCE_CALLER="${GUIDANCE_CALLER:-$PROJECT_ROOT/src/foho/guidance/run.py}"
OUTER_LAUNCHER="${OUTER_LAUNCHER:-$PROJECT_ROOT/scripts/phase1/run_selector_v41_full_pipeline_one.sh}"
CPU_7DOF_SOURCE="${CPU_7DOF_SOURCE:-$PROJECT_ROOT/tools/gate_c_v99_11_hand_anchor/run_v3_CPU_7DoF_global_hand_alignment_v99_11_7_13_3_6.py}"
GATE_D_PARENT="${GATE_D_PARENT:-$PROJECT_ROOT/scripts/phase2/gate_d0_fit_v1_articulated_fit.py}"

HANDOFF_ROOT="${HANDOFF_ROOT:-$HAND_ROOT/frozen_s100_up_pipeline_handoff_v99_11_7_13_3_13}"
OBJECT_GPU_ROOT="${OBJECT_GPU_ROOT:-$HAND_ROOT/object_only_gpu_v99_11_7_13_3_14}"
JOINT_GPU_ROOT="${JOINT_GPU_ROOT:-$HAND_ROOT/joint_flow_gpu_v99_11_7_13_3_16}"

mkdir -p \
  "$HANDOFF_ROOT"/{config,evidence,hashes,reports,launch} \
  "$OBJECT_GPU_ROOT"/{config,evidence,preflight,launch,run,reports,checkpoints,hashes} \
  "$JOINT_GPU_ROOT"/{config,evidence,preflight,launch,run,reports,checkpoints,hashes}

PASS=0
HOLD=0
check_file() {
  local label="$1"
  local path="$2"
  if [[ -s "$path" ]]; then
    printf '[PASS] %s=%s\n' "$label" "$path"
    PASS=$((PASS + 1))
  else
    printf '[HOLD] %s_MISSING=%s\n' "$label" "$path"
    HOLD=$((HOLD + 1))
  fi
}

check_file PIPE_PARENT "$PIPE_PARENT"
check_file GUIDANCE_CALLER "$GUIDANCE_CALLER"
check_file OUTER_LAUNCHER "$OUTER_LAUNCHER"
check_file CPU_7DOF_SOURCE "$CPU_7DOF_SOURCE"
check_file GATE_D_PARENT "$GATE_D_PARENT"

if command -v rg >/dev/null 2>&1; then
  if [[ -s "$PIPE_PARENT" ]]; then
    rg -n -C 5 \
      'get_guidance_params|phase[[:space:]]*=[[:space:]]*1([^.]|$)|phase[[:space:]]*=[[:space:]]*1\.5|phase[[:space:]]*=[[:space:]]*2|noise_pred_obj|scheduler\.step|scale_hand|trans_hand|translation_hand|rotation_hand' \
      "$PIPE_PARENT" \
      > "$HANDOFF_ROOT/evidence/staged_optimizer_trace.txt" || true
  fi

  if [[ -s "$GUIDANCE_CALLER" ]]; then
    rg -n -C 6 \
      'def run_hunyuan_w_guid|def run\(|pipeline\(|h2m_rt_path|aligned_mano_mesh_path|hunyuan_hoi_mesh_path|guidance_out_dir|already exists, skipping' \
      "$GUIDANCE_CALLER" \
      > "$HANDOFF_ROOT/evidence/guidance_caller_trace.txt" || true
  fi

  if [[ -s "$OUTER_LAUNCHER" ]]; then
    rg -n -C 4 \
      'CASE=|RUN_ID=|CFG=|source .*CFG|python|foho\.main|guidance|GEMINI_RESPONSES|FOHO_FINAL_OCTREE_RES|PYTORCH_CUDA_ALLOC_CONF' \
      "$OUTER_LAUNCHER" \
      > "$HANDOFF_ROOT/evidence/outer_launcher_trace.txt" || true
  fi

  rg -n -C 3 \
    'PYTORCH_CUDA_ALLOC_CONF|cudaMallocAsync|FOHO_FINAL_OCTREE_RES|FOHO_RENDER_SCALE|FOHO_OPT_STEPS_SCALE|optimization_steps_scale|optimization_steps_joint|noise_obj_lr1|noise_obj_lr2' \
    "$PROJECT_ROOT" "$DATA_ROOT" 2>/dev/null \
    > "$HANDOFF_ROOT/evidence/low_memory_and_schedule_trace.txt" || true
fi

python3 - "$PIPE_PARENT" "$GUIDANCE_CALLER" "$OUTER_LAUNCHER" "$HANDOFF_ROOT/evidence/source_api_audit.json" <<'PY'
from __future__ import annotations
from pathlib import Path
import ast
import json
import re
import sys

pipe = Path(sys.argv[1])
caller = Path(sys.argv[2])
launcher = Path(sys.argv[3])
out = Path(sys.argv[4])

report: dict[str, object] = {
    "schema": "hoiso_source_api_audit_v1",
    "pipeline": {"path": str(pipe), "exists": pipe.is_file()},
    "guidance_caller": {"path": str(caller), "exists": caller.is_file()},
    "outer_launcher": {"path": str(launcher), "exists": launcher.is_file()},
    "authorization": {
        "gpu_execution": False,
        "object_only": False,
        "joint_flow": False,
    },
}

def inspect_python(path: Path) -> dict[str, object]:
    result: dict[str, object] = {"classes": [], "functions": [], "call_sites": []}
    if not path.is_file():
        return result
    text = path.read_text(errors="replace")
    try:
        tree = ast.parse(text)
    except Exception as exc:
        result["ast_error"] = f"{type(exc).__name__}: {exc}"
        return result
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            result["classes"].append({"name": node.name, "line": node.lineno})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [arg.arg for arg in node.args.args]
            if node.args.vararg:
                args.append("*" + node.args.vararg.arg)
            if node.args.kwarg:
                args.append("**" + node.args.kwarg.arg)
            if (
                node.name in {"run", "run_hunyuan_w_guid", "__call__"}
                or "guidance" in node.name.lower()
                or "pipeline" in node.name.lower()
            ):
                result["functions"].append(
                    {"name": node.name, "line": node.lineno, "args": args}
                )
        elif isinstance(node, ast.Call):
            name = None
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name in {"pipeline", "run_hunyuan_w_guid", "step"}:
                result["call_sites"].append({"name": name, "line": node.lineno})
    return result

report["pipeline"]["api"] = inspect_python(pipe)
report["guidance_caller"]["api"] = inspect_python(caller)

if launcher.is_file():
    text = launcher.read_text(errors="replace")
    report["outer_launcher"]["case_positional"] = bool(re.search(r'CASE=.*\$\{?1', text))
    report["outer_launcher"]["config_source_present"] = "source" in text and "CFG" in text
    report["outer_launcher"]["python_lines"] = [
        line.strip() for line in text.splitlines()
        if "python" in line or "foho.main" in line or "guidance" in line
    ]

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2) + "\n")
print(f"[PASS] SOURCE_API_AUDIT={out}")
PY

mapfile -t SEVEN_DOF_RESULTS < <(
  find "$HAND_ROOT" -type f \
    -name 'CPU_7DoF_global_hand_result_s100_up_v99_11_7_9_21_7_13_3_8_2.npz' \
    -print 2>/dev/null | sort
)
mapfile -t FAST_ROUTES < <(
  find "$HAND_ROOT" -type f \
    -name 'object_then_joint_flow_fast_track_route_v99_11_7_9_21_7_13_3_12_3.json' \
    -print 2>/dev/null | sort
)
mapfile -t HANDOFF_POLICIES < <(
  find "$HAND_ROOT" -type f \
    -name 'frozen_anchor_pipeline_handoff_source_authorization_v99_11_7_9_21_7_13_3_12_3.json' \
    -print 2>/dev/null | sort
)

SEVEN_DOF_RESULT=""
FAST_ROUTE=""
HANDOFF_POLICY=""

if [[ ${#SEVEN_DOF_RESULTS[@]} -eq 1 ]]; then
  SEVEN_DOF_RESULT="${SEVEN_DOF_RESULTS[0]}"
  printf '[PASS] SEVEN_DOF_RESULT=%s\n' "$SEVEN_DOF_RESULT"
else
  printf '[HOLD] SEVEN_DOF_RESULT_MATCH_COUNT=%s\n' "${#SEVEN_DOF_RESULTS[@]}"
fi
if [[ ${#FAST_ROUTES[@]} -eq 1 ]]; then
  FAST_ROUTE="${FAST_ROUTES[0]}"
  printf '[PASS] FAST_ROUTE=%s\n' "$FAST_ROUTE"
else
  printf '[HOLD] FAST_ROUTE_MATCH_COUNT=%s\n' "${#FAST_ROUTES[@]}"
fi
if [[ ${#HANDOFF_POLICIES[@]} -eq 1 ]]; then
  HANDOFF_POLICY="${HANDOFF_POLICIES[0]}"
  printf '[PASS] HANDOFF_POLICY=%s\n' "$HANDOFF_POLICY"
else
  printf '[HOLD] HANDOFF_POLICY_MATCH_COUNT=%s\n' "${#HANDOFF_POLICIES[@]}"
fi

mapfile -t ACCEPTED_OBJECTS < <(
  find "$CASE_ROOT" -type f \
    \( -iname '*gate_a_verified_object_canonical.ply' \
       -o -iname '*accepted*part*aware*.ply' \
       -o -iname '*accepted*complete*laptop*.ply' \
       -o -iname '*repaired*object*.ply' \) \
    -print 2>/dev/null | sort -u
)
printf '%s\n' "${ACCEPTED_OBJECTS[@]:-}" \
  > "$HANDOFF_ROOT/evidence/accepted_object_candidates.txt"
if [[ ${#ACCEPTED_OBJECTS[@]} -eq 1 ]]; then
  printf '[PASS] ACCEPTED_OBJECT_CANDIDATE=%s\n' "${ACCEPTED_OBJECTS[0]}"
else
  printf '[HOLD] ACCEPTED_OBJECT_CANDIDATE_COUNT=%s\n' "${#ACCEPTED_OBJECTS[@]}"
fi

HASH_INPUTS=("$PIPE_PARENT" "$GUIDANCE_CALLER" "$OUTER_LAUNCHER" "$CPU_7DOF_SOURCE" "$GATE_D_PARENT")
[[ -n "$SEVEN_DOF_RESULT" ]] && HASH_INPUTS+=("$SEVEN_DOF_RESULT")
[[ -n "$FAST_ROUTE" ]] && HASH_INPUTS+=("$FAST_ROUTE")
[[ -n "$HANDOFF_POLICY" ]] && HASH_INPUTS+=("$HANDOFF_POLICY")
for path in "${ACCEPTED_OBJECTS[@]:-}"; do
  [[ -s "$path" ]] && HASH_INPUTS+=("$path")
done
sha256sum "${HASH_INPUTS[@]}" \
  > "$HANDOFF_ROOT/hashes/frozen_source_and_state_inputs.sha256" 2>/dev/null || true

python3 - "$OBJECT_GPU_ROOT/config/object_only_scope.json" "$JOINT_GPU_ROOT/config/joint_flow_scope.json" "$HANDOFF_ROOT/launch/launch_contract.template.json" "$PROJECT_ROOT" "$CASE_ROOT" "$PIPE_PARENT" "$GUIDANCE_CALLER" "$OUTER_LAUNCHER" "$SEVEN_DOF_RESULT" "$FAST_ROUTE" "$HANDOFF_POLICY" <<'PY'
from pathlib import Path
import json
import sys

object_scope = Path(sys.argv[1])
joint_scope = Path(sys.argv[2])
launch = Path(sys.argv[3])
project_root, case_root, pipe, caller, launcher, anchor, route, policy = sys.argv[4:]

object_data = {
    "schema": "hoiso_object_only_gpu_scope_v2",
    "case_id": "alapuse02v3n60",
    "hand_anchor": "s100_up",
    "stage": "implementation_phase_1_5_paper_phase_2_object_only",
    "required_before_execution": [
        "unique_source_bound_anchor",
        "778_vertex_external_anchor_roundtrip",
        "accepted_object_state_classified_as_mesh_only_or_latent_backed",
        "accepted_object_zero_update_identity",
        "literal_historical_caller_command_frozen",
        "source_proven_low_memory_settings",
        "separate_output_directory_and_skip_check_disabled_or_avoided",
    ],
    "frozen": [
        "hand_identity", "hand_topology", "hand_shape",
        "local_mano_articulation", "accepted_s100_up_anchor"
    ],
    "closed": [
        "joint_flow", "contact", "collision", "Gate_D",
        "new_hamer_run", "new_object_reconstruction"
    ],
    "authorizes_gpu_execution": False,
}

joint_data = {
    "schema": "hoiso_joint_flow_gpu_scope_v2",
    "case_id": "alapuse02v3n60",
    "stage": "implementation_phase_2_paper_phase_3_joint",
    "required_before_execution": [
        "object_only_independent_review_pass",
        "accepted_post_object_checkpoint_hash",
        "source_proven_delta_composition_order",
        "noise_pred_obj_gradient_and_scheduler_receipt_instrumentation",
        "hard_hand_and_object_trust_envelopes",
        "rollback_checkpoint"
    ],
    "frozen": ["local_mano_articulation"],
    "closed": ["contact", "collision", "Gate_D"],
    "authorizes_gpu_execution": False,
}

launch_data = {
    "schema": "hoiso_object_then_joint_launch_contract_template_v2",
    "project_root": project_root,
    "case_root": case_root,
    "source_chain": {
        "outer_launcher": launcher,
        "guidance_caller": caller,
        "pipeline_source": pipe,
    },
    "frozen_hand_anchor_npz": anchor or None,
    "fast_track_route": route or None,
    "handoff_policy": policy or None,
    "accepted_object": {
        "state_class": None,
        "mesh_path": None,
        "latent_path": None,
        "noise_state_path": None,
        "seed": None,
        "zero_update_identity_report": None,
    },
    "object_only": {
        "literal_command": None,
        "config_path": None,
        "step_count": None,
        "learning_rates_source": None,
        "trust_region": None,
        "output_dir": None,
        "authorized": False,
    },
    "joint_flow": {
        "literal_command": None,
        "config_path": None,
        "step_count": None,
        "learning_rates_source": None,
        "hand_delta_composition": None,
        "trust_region": None,
        "noise_pred_obj_receipt": None,
        "output_dir": None,
        "authorized": False,
    },
    "global_authorization": {
        "gpu_model_load": False,
        "object_only_execution": False,
        "joint_flow_execution": False,
        "Gate_D": False,
    },
}

for path, data in ((object_scope, object_data), (joint_scope, joint_data), (launch, launch_data)):
    if path.exists():
        print(f"[HOLD] NO_CLOBBER_EXISTING={path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n")
        print(f"[PASS] WROTE={path}")
PY

printf '[INFO] PASS_COUNT=%s HOLD_COUNT=%s\n' "$PASS" "$HOLD"
printf '[INFO] PREPARATION_ONLY=TRUE\n'
printf '[INFO] GPU_MODEL_LOAD=FALSE\n'
printf '[INFO] OPTIMIZATION_EXECUTED=FALSE\n'
printf '[INFO] NEXT=review source API audit, classify accepted object as mesh-only or latent-backed, implement opt-in handoff, then run zero-update identities\n'
