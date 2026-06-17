#!/usr/bin/env python
from pathlib import Path
import json
import shutil
import pandas as pd

PHASE1 = Path("/home/fredcui/foho_phase0/phase1_diagnostics")
SRC = PHASE1 / "selector_v4_action_simulation"
FINAL = PHASE1 / "selector_v4_selected_only_outputs"
SUMMARY = SRC / "selector_v4_action_simulation_summary.csv"

FINAL.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SUMMARY)
rows = []

for _, r in df.iterrows():
    case = r["case"]
    decision = r["final_decision"]

    case_dir = FINAL / case
    case_dir.mkdir(parents=True, exist_ok=True)

    record = {
        "case": case,
        "sample_id": r["sample_id"],
        "method": r["method"],
        "final_decision": decision,
        "source_action": r["action"],
        "failure_reasons": r.get("failure_reasons", ""),
    }

    if decision == "select":
        src_dir = SRC / "accepted_outputs" / case

        for name in ["pred_hand_aligned.ply", "pred_object_aligned.ply"]:
            src = src_dir / name
            dst = case_dir / name
            if src.exists():
                shutil.copy2(src, dst)
                record[f"final_{name}"] = str(dst)
            else:
                record[f"missing_{name}"] = str(src)

        record["replacement_status"] = "final_selected_output_created"
    else:
        record["replacement_status"] = "no_final_output_rejected"
        (case_dir / "rejection_report.json").write_text(json.dumps(record, indent=2))

    rows.append(record)

out = pd.DataFrame(rows)
out.to_csv(FINAL / "selector_v4_selected_only_summary.csv", index=False)
(FINAL / "selector_v4_selected_only_summary.json").write_text(json.dumps(rows, indent=2))

print("[OK] wrote", FINAL)
print(out[[
    "case", "sample_id", "method",
    "final_decision", "replacement_status", "failure_reasons"
]].to_string(index=False))
