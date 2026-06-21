#!/usr/bin/env python
from pathlib import Path
import pandas as pd

EXP_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance")
CSV = EXP_OUT / "arctic5_selector_combined_performance.csv"
OUT = EXP_OUT / "arctic5_replacement_dryrun_decisions.csv"

df = pd.read_csv(CSV)

rows = []

for case, sub in df.groupby("case"):
    pass_rows = sub[sub["selector_v4_gate"] == "pass"].copy()

    if len(pass_rows) > 0:
        pass_rows = pass_rows.sort_values(["object_cd_mm"], ascending=True)
        chosen = pass_rows.iloc[0]
        rows.append({
            "case": case,
            "dryrun_decision": "would_replace_with_safe_candidate",
            "chosen_method": chosen["method"],
            "chosen_run_id": chosen["run_id"],
            "reason": "candidate passes selector-v4 physical gate",
            "next_action": "visual_confirm_then_copy_to_final_selected_outputs",
        })
        continue

    part = sub[sub["method"] == "partaware_v2_attempt0"]
    if len(part) == 0 or part.iloc[0]["final_status"] == "missing_rerun":
        rows.append({
            "case": case,
            "dryrun_decision": "no_replacement_missing_partaware_attempt0",
            "chosen_method": "",
            "chosen_run_id": "",
            "reason": "no selector-v4 pass and partaware attempt0 missing",
            "next_action": "run_partaware_attempt0_or_optional_ablation",
        })
        continue

    gate = str(part.iloc[0]["selector_v4_gate"])
    if "penetration" in gate:
        action = "run_attempt1_reinpaint_or_contact_aware_guidance"
    elif "floating" in gate:
        action = "run_attempt1_repose_or_contact_aware_guidance"
    else:
        action = "manual_review"

    rows.append({
        "case": case,
        "dryrun_decision": "no_safe_replacement",
        "chosen_method": "",
        "chosen_run_id": "",
        "reason": f"partaware attempt0 exists but {gate}",
        "next_action": action,
    })

out = pd.DataFrame(rows)
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(out.to_string(index=False))
