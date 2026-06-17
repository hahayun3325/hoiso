#!/usr/bin/env python
from pathlib import Path
import json
import shutil
import pandas as pd

PHASE1 = Path("/home/fredcui/foho_phase0/phase1_diagnostics")
IO_DIR = PHASE1 / "io_alignment"
SEL = PHASE1 / "selector_v4_pipeline_dryrun/selector_v4_pipeline_dryrun_selected_cases.csv"
OUT = PHASE1 / "selector_v4_action_simulation"

ACCEPT = OUT / "accepted_outputs"
REJECT = OUT / "rejected_cases"
ACCEPT.mkdir(parents=True, exist_ok=True)
REJECT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SEL)

rows = []

for _, r in df.iterrows():
    case = r["case"]
    sample_id = r["sample_id"]
    decision = r["final_decision"]
    method = r["method"]

    src_dir = IO_DIR / sample_id

    record = {
        "case": case,
        "sample_id": sample_id,
        "method": method,
        "final_decision": decision,
        "failure_reasons": r.get("failure_reasons", ""),
        "p5_hand_object_dist_mm": float(r["p5_hand_object_dist_mm"]),
        "floating": bool(r["floating"]),
        "object_inside_hand_ratio": float(r["object_inside_hand_ratio"]),
        "hand_inside_object_ratio": float(r["hand_inside_object_ratio"]),
    }

    if decision == "select":
        dst_dir = ACCEPT / case
        dst_dir.mkdir(parents=True, exist_ok=True)

        for name in ["pred_hand_aligned.ply", "pred_object_aligned.ply"]:
            src = src_dir / name
            dst = dst_dir / name
            if src.exists():
                shutil.copy2(src, dst)
                record[f"copied_{name}"] = str(dst)
            else:
                record[f"missing_{name}"] = str(src)

        record["action"] = "accepted_copy_created"

    else:
        dst_dir = REJECT / case
        dst_dir.mkdir(parents=True, exist_ok=True)

        record["action"] = "rejected_no_output_copy"
        (dst_dir / "rejection_report.json").write_text(json.dumps(record, indent=2))

    rows.append(record)

summary = pd.DataFrame(rows)
summary.to_csv(OUT / "selector_v4_action_simulation_summary.csv", index=False)
(OUT / "selector_v4_action_simulation_summary.json").write_text(
    json.dumps(rows, indent=2)
)

print("[OK] wrote", OUT)
print(summary[[
    "case", "sample_id", "method", "final_decision",
    "action", "failure_reasons"
]].to_string(index=False))
