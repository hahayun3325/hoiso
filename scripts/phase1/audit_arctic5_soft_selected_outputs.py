#!/usr/bin/env python
from pathlib import Path
import json
import os
import pandas as pd

SOFT_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_soft_selected_outputs")
MANIFEST = SOFT_OUT / "arctic5_soft_selected_manifest.csv"
OUT = SOFT_OUT / "arctic5_soft_selected_audit.csv"

df = pd.read_csv(MANIFEST)
rows = []

ok = True

for _, r in df.iterrows():
    case = r["case"]
    case_dir = SOFT_OUT / case
    hand = Path(r["soft_selected_hand"])
    obj = Path(r["soft_selected_object"])
    decision_json = case_dir / "selector_v4_1_decision.json"

    hand_exists = hand.exists()
    obj_exists = obj.exists()
    decision_exists = decision_json.exists()

    hand_target = os.readlink(hand) if hand.is_symlink() else str(hand)
    obj_target = os.readlink(obj) if obj.is_symlink() else str(obj)

    decision = {}
    if decision_exists:
        decision = json.loads(decision_json.read_text())

    row_ok = (
        hand_exists
        and obj_exists
        and decision_exists
        and decision.get("is_final_physical_output") is False
        and decision.get("next_stage") == "contact_aware_optimization"
    )

    ok = ok and row_ok

    rows.append({
        "case": case,
        "method": r["method"],
        "run_id": r["run_id"],
        "hand_exists": hand_exists,
        "object_exists": obj_exists,
        "decision_json_exists": decision_exists,
        "hand_target": hand_target,
        "object_target": obj_target,
        "next_stage": decision.get("next_stage", ""),
        "is_final_physical_output": decision.get("is_final_physical_output", ""),
        "audit_ok": row_ok,
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(out.to_string(index=False))
print("all_audit_ok =", ok)

if not ok:
    raise SystemExit("[BAD] soft selection audit failed")
