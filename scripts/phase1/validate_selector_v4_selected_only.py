#!/usr/bin/env python
from pathlib import Path
import json
import pandas as pd

PHASE1 = Path("/home/fredcui/foho_phase0/phase1_diagnostics")
OUT = PHASE1 / "selector_v4_selected_only_outputs"
SUMMARY = OUT / "selector_v4_selected_only_summary.csv"

df = pd.read_csv(SUMMARY)
rows = []

for _, r in df.iterrows():
    case = r["case"]
    decision = r["final_decision"]
    case_dir = OUT / case

    hand = case_dir / "pred_hand_aligned.ply"
    obj = case_dir / "pred_object_aligned.ply"
    rej = case_dir / "rejection_report.json"

    if decision == "select":
        ok = hand.exists() and obj.exists() and not rej.exists()
        status = "OK" if ok else "FAIL"
        note = "selected case has both meshes" if ok else "selected case missing meshes or has rejection report"
    else:
        ok = rej.exists() and not hand.exists() and not obj.exists()
        status = "OK" if ok else "FAIL"
        note = "rejected case has report and no copied meshes" if ok else "rejected case missing report or has copied meshes"

    rows.append({
        "case": case,
        "decision": decision,
        "status": status,
        "note": note,
        "has_hand_mesh": hand.exists(),
        "has_object_mesh": obj.exists(),
        "has_rejection_report": rej.exists(),
    })

res = pd.DataFrame(rows)
out_csv = OUT / "selector_v4_selected_only_validation.csv"
out_json = OUT / "selector_v4_selected_only_validation.json"

res.to_csv(out_csv, index=False)
out_json.write_text(json.dumps(rows, indent=2))

print("[Validation]")
print(res.to_string(index=False))
print("\nall_ok =", bool((res["status"] == "OK").all()))
