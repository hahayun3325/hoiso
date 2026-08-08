#!/usr/bin/env bash
set -uo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/home/fredcui/Projects/FollowMyHold}"
DATA_ROOT="${DATA_ROOT:-/home/fredcui/foho_phase0}"
CASE_ROOT="${CASE_ROOT:-$DATA_ROOT/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2}"
HAND_ANCHOR_ROOT="${HAND_ANCHOR_ROOT:-$CASE_ROOT/gate_c_hand_anchor}"
V99_11_7_ROOT="${V99_11_7_ROOT:-$HAND_ANCHOR_ROOT/v99_11_7_hand_anchor_gate_policy}"
V99_11_7_9_ROOT="${V99_11_7_9_ROOT:-$V99_11_7_ROOT/sequential_reanchor_collection_v99_11_7_9}"
V99_11_7_9_11_ROOT="${V99_11_7_9_11_ROOT:-$V99_11_7_9_ROOT/six_metric_calibration_execution_v99_11_7_9_11}"
CALIBRATION_RUN_ROOT="$V99_11_7_9_11_ROOT/run/one_cpu_calibration"

CANDIDATE_TABLE="$CALIBRATION_RUN_ROOT/six_metric_v6_candidate_table_v99_11_7_9_11.json"
THRESHOLD_BUNDLE="$CALIBRATION_RUN_ROOT/six_metric_v6_threshold_bundle_v99_11_7_9_11.json"
CALIBRATION_REPORT="$CALIBRATION_RUN_ROOT/six_metric_v6_calibration_report_v99_11_7_9_11.json"
INDEPENDENT_REVIEW="$V99_11_7_9_11_ROOT/evidence/cpu_calibration_independent_review_v99_11_7_9_11.json"
GATE_APPLICATION="$V99_11_7_9_11_ROOT/reports/frozen_six_metric_gate_application_v99_11_7_9_11.json"
POST_CALIBRATION_ROUTE="$V99_11_7_9_11_ROOT/reports/post_calibration_route_v99_11_7_9_11.json"

V99_11_7_9_12_ROOT="${V99_11_7_9_12_ROOT:-$V99_11_7_9_ROOT/indexed_identity_critic_v99_11_7_9_12}"
mkdir -p \
  "$V99_11_7_9_12_ROOT/config" \
  "$V99_11_7_9_12_ROOT/evidence" \
  "$V99_11_7_9_12_ROOT/reports" \
  "$V99_11_7_9_12_ROOT/visuals" \
  "$V99_11_7_9_12_ROOT/notes" \
  "$V99_11_7_9_12_ROOT/hashes"

for path in \
  "$CANDIDATE_TABLE" \
  "$THRESHOLD_BUNDLE" \
  "$CALIBRATION_REPORT" \
  "$INDEPENDENT_REVIEW" \
  "$GATE_APPLICATION" \
  "$POST_CALIBRATION_ROUTE"; do
  if test -s "$path"; then
    echo "[PASS] CURRENT_INPUT=$path"
  else
    echo "[HOLD] CURRENT_INPUT_MISSING=$path"
  fi
done

SCOPE="$V99_11_7_9_12_ROOT/config/indexed_identity_critic_scope_v99_11_7_9_12.json"
if ! test -e "$SCOPE"; then
cat > "$SCOPE" <<'JSON'
{
  "schema": "indexed_identity_critic_scope_v99_11_7_9_12",
  "positive_control_case": "alapuse02v6n60",
  "input_population": "survivors_from_frozen_six_metric_gate_v99_11_7_9_11",
  "allowed": [
    "bind_survivor_uids",
    "indexed_identity_review",
    "physical_hand_identity",
    "laterality_review",
    "wrist_palm_orientation_review",
    "visible_finger_chain_review",
    "reject_or_survive"
  ],
  "closed": [
    "change_crop_lattice",
    "refit_numeric_thresholds",
    "run_hamer_again",
    "run_v3",
    "select_by_v3_performance",
    "optimizer",
    "contact",
    "collision",
    "flow",
    "C2",
    "F3_4",
    "Gate_D"
  ],
  "authorizes_v3": false,
  "authorizes_optimizer": false
}
JSON
  echo "[PASS] CREATED_SCOPE=$SCOPE"
else
  echo "[INFO] PRESERVED_SCOPE=$SCOPE"
fi

JSON_FORM="$V99_11_7_9_12_ROOT/config/indexed_identity_review_form_v99_11_7_9_12.json"
CSV_FORM="$V99_11_7_9_12_ROOT/config/indexed_identity_review_form_v99_11_7_9_12.csv"

python3 - "$POST_CALIBRATION_ROUTE" "$JSON_FORM" "$CSV_FORM" <<'PY'
from pathlib import Path
import csv
import json
import sys

route_path = Path(sys.argv[1])
json_out = Path(sys.argv[2])
csv_out = Path(sys.argv[3])

if not route_path.is_file():
    print(f"[HOLD] ROUTE_MISSING={route_path}")
else:
    try:
        route = json.loads(route_path.read_text())
        survivors = list(route.get("survivors", []))
        expected = "prepare_v99_11_7_9_12_indexed_identity_critic_for_quantitative_survivors"
        if route.get("decision") != expected:
            print(f"[HOLD] WRONG_ROUTE={route.get('decision')}")
        elif len(survivors) <= 1:
            print(f"[HOLD] SURVIVOR_COUNT_NOT_MULTIPLE={len(survivors)}")
        elif json_out.exists() or csv_out.exists():
            print(f"[INFO] PRESERVED_REVIEW_FORM=json:{json_out.exists()} csv:{csv_out.exists()}")
        else:
            rows = [{
                "candidate_uid": uid,
                "physical_hand_match": None,
                "laterality_plausible": None,
                "wrist_palm_orientation_plausible": None,
                "visible_finger_chain_plausible": None,
                "reject": None,
                "reason": ""
            } for uid in survivors]
            packet = {
                "schema": "indexed_identity_review_form_v99_11_7_9_12",
                "candidate_order": survivors,
                "rows": rows,
                "selection_performed": False,
                "authorizes_v3": False,
                "authorizes_optimizer": False
            }
            json_out.write_text(json.dumps(packet, indent=2) + "\n")
            with csv_out.open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            print(f"[PASS] IDENTITY_JSON={json_out}")
            print(f"[PASS] IDENTITY_CSV={csv_out}")
            print(f"[INFO] REVIEW_COUNT={len(rows)}")
    except Exception as error:
        print(f"[HOLD] REVIEW_FORM_FAILED={type(error).__name__}:{error}")
PY

if command -v sha256sum >/dev/null 2>&1; then
  for path in "$CANDIDATE_TABLE" "$THRESHOLD_BUNDLE" "$CALIBRATION_REPORT" \
              "$INDEPENDENT_REVIEW" "$GATE_APPLICATION" "$POST_CALIBRATION_ROUTE"; do
    test -s "$path" && sha256sum "$path"
  done > "$V99_11_7_9_12_ROOT/hashes/frozen_v99_11_7_9_11_inputs.sha256"
  echo "[PASS] HASH_MANIFEST=$V99_11_7_9_12_ROOT/hashes/frozen_v99_11_7_9_11_inputs.sha256"
fi

echo "[HOLD] NEXT=COMPLETE_INDEXED_IDENTITY_REVIEW_ONLY"
echo "[HOLD] V3_EXECUTION=false"
echo "[HOLD] OPTIMIZER=false"
