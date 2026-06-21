#!/usr/bin/env python
from pathlib import Path
import pandas as pd

EXP_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance")
DRYRUN = EXP_OUT / "arctic5_replacement_dryrun_decisions.csv"
OUT = EXP_OUT / "arctic5_next_actions_v2.csv"

df = pd.read_csv(DRYRUN)

priority_map = {
    "run_attempt1_reinpaint_or_contact_aware_guidance": "high",
    "run_attempt1_repose_or_contact_aware_guidance": "high",
    "run_partaware_attempt0_or_optional_ablation": "medium",
    "visual_confirm_then_copy_to_final_selected_outputs": "medium",
    "manual_review": "medium",
}

rows = []
for _, r in df.iterrows():
    action = r["next_action"]
    rows.append({
        "case": r["case"],
        "dryrun_decision": r["dryrun_decision"],
        "reason": r["reason"],
        "next_action": action,
        "priority": priority_map.get(action, "medium"),
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)
print("[OK] wrote", OUT)
print(out.to_string(index=False))
