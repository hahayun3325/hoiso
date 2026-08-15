#!/usr/bin/env bash
# Read-only bootstrap for the v6 accepted-path consumption audit.
# It creates a versioned workspace and inventories source/artifacts. It never
# edits the repository, moves meshes, or launches an optimizer.

set -u
set -o pipefail

pass() { printf '[PASS] %s\n' "$*"; }
hold() { printf '[HOLD] %s\n' "$*" >&2; }
info() { printf '[INFO] %s\n' "$*"; }

REPO="${REPO:-/home/fredcui/Projects/FollowMyHold}"
DATA="${DATA:-/home/fredcui/foho_phase0}"
V6_CASE_ROOT="${V6_CASE_ROOT:-$DATA/phase2_gateA_part_recon/cases/alapuse02_v6_n60}"
V6_RUN_ROOT="${V6_RUN_ROOT:-$DATA/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse02v6n60_selector_v41_refined_pipeline}"
V3_CASE_ROOT="${V3_CASE_ROOT:-$DATA/vlm_failure_containment/alapuse02v3n60/inpainting_fallback/automatic_recovery_v2_part_graph}"
AUDIT_ROOT="${AUDIT_ROOT:-$V6_CASE_ROOT/gate_c0_v6_consumption_path_audit_v1}"
TOOL_ROOT="${TOOL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"

missing=0
for item in "$REPO" "$DATA" "$V6_CASE_ROOT" "$V6_RUN_ROOT"; do
  if [[ -d "$item" ]]; then
    pass "ROOT=$item"
  else
    hold "ROOT_MISSING=$item"
    missing=1
  fi
done
if [[ "$missing" -ne 0 ]]; then
  info "Locate the actual v6 roots before rerunning:"
  find "$DATA" -maxdepth 8 -type d \
    \( -iname '*alapuse02_v6_n60*' -o -iname '*alapuse02v6n60*' \) \
    -print 2>/dev/null | sort | head -n 160 || true
  exit 1
fi

mkdir -p \
  "$AUDIT_ROOT/inventory" \
  "$AUDIT_ROOT/manifests" \
  "$AUDIT_ROOT/decision" \
  "$AUDIT_ROOT/preregistration" \
  "$AUDIT_ROOT/notes"

if [[ ! -f "$AUDIT_ROOT/manifests/v6_loss_input_manifest.csv" ]]; then
  cp "$TOOL_ROOT/templates/v6_loss_input_manifest.csv" \
    "$AUDIT_ROOT/manifests/v6_loss_input_manifest.csv"
  pass "MANIFEST_TEMPLATE_WRITTEN=$AUDIT_ROOT/manifests/v6_loss_input_manifest.csv"
else
  info "Manifest already exists; preserving it."
fi

if [[ ! -f "$AUDIT_ROOT/notes/manual_review_notes.md" ]]; then
  cp "$TOOL_ROOT/templates/route_decision_notes.md" \
    "$AUDIT_ROOT/notes/manual_review_notes.md"
fi

{
  echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "repo=$REPO"
  echo "data=$DATA"
  echo "v6_case_root=$V6_CASE_ROOT"
  echo "v6_run_root=$V6_RUN_ROOT"
  echo "v3_case_root=$V3_CASE_ROOT"
  echo "audit_root=$AUDIT_ROOT"
  echo "tool_root=$TOOL_ROOT"
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
  }
) > "$AUDIT_ROOT/inventory/git_state.txt"

V3_ARGS=()
if [[ -d "$V3_CASE_ROOT" ]]; then
  V3_ARGS=(--v3-case-root "$V3_CASE_ROOT")
else
  hold "OPTIONAL_V3_CASE_ROOT_MISSING=$V3_CASE_ROOT"
  find "$DATA" -maxdepth 9 -type d -iname '*alapuse02v3n60*' -print \
    2>/dev/null | sort > "$AUDIT_ROOT/inventory/v3_case_root_candidates.txt" || true
fi

python "$TOOL_ROOT/scripts/inventory_v6_consumption_paths.py" \
  --repo "$REPO" \
  --v6-case-root "$V6_CASE_ROOT" \
  --v6-run-root "$V6_RUN_ROOT" \
  "${V3_ARGS[@]}" \
  --out-dir "$AUDIT_ROOT/inventory"
status=$?
if [[ "$status" -ne 0 ]]; then
  hold "INVENTORY_FAILED status=$status"
  exit "$status"
fi

cat > "$AUDIT_ROOT/decision/HOLD_CURRENT_STAGE.md" <<'MD'
# Current authorization state

The v6 consumption path has not yet been classified.

Until the loss-input manifest is source-confirmed and the route decision is
written, the following remain **not authorized**:

- changing the live helper;
- rewriting the v3 target;
- scoring hand candidates;
- moving the hand or laptop;
- MANO articulation;
- C2;
- F3.4;
- Gate D.
MD

pass "V6_CONSUMPTION_AUDIT_WORKSPACE_READY=$AUDIT_ROOT"
info "Review: $AUDIT_ROOT/inventory/summary.md"
info "Review: $AUDIT_ROOT/inventory/source_hits.tsv"
info "Fill:   $AUDIT_ROOT/manifests/v6_loss_input_manifest.csv"
info "Then run classify_v6_control.py; do not launch optimization."
