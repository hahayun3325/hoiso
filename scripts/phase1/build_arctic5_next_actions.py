#!/usr/bin/env python
from pathlib import Path
import pandas as pd

EXP_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance")
COMBINED = EXP_OUT / "arctic5_selector_combined_performance.csv"
OUT = EXP_OUT / "arctic5_next_actions.csv"

df = pd.read_csv(COMBINED)

cases = ["abox01", "aket01", "ascis01", "alapuse01", "amicuse01"]
rows = []

for case in cases:
    sub = df[df["case"] == case]

    part = sub[sub["method"] == "partaware_v2_attempt0"]

    if case == "aket01":
        rows.append({
            "case": case,
            "next_action": "run_attempt1_reinpaint_fallback",
            "reason": "partaware attempt0 exists but selector-v4 rejects severe penetration",
            "priority": "high",
            "policy_role": "required_after_attempt0_failure",
        })
        continue

    if len(part) == 0 or part.iloc[0]["final_status"] == "missing_rerun":
        if case == "alapuse01":
            rows.append({
                "case": case,
                "next_action": "optional_run_partaware_attempt0_ablation",
                "reason": "originally selected/usable case, but useful for complete 5-case comparison",
                "priority": "medium",
                "policy_role": "optional_ablation",
            })
        else:
            rows.append({
                "case": case,
                "next_action": "run_partaware_attempt0",
                "reason": "partaware attempt0 missing; old candidates rejected or physically weak",
                "priority": "high",
                "policy_role": "required_comparison",
            })
    else:
        rows.append({
            "case": case,
            "next_action": "inspect_existing_partaware_attempt0",
            "reason": "partaware attempt0 already exists",
            "priority": "medium",
            "policy_role": "existing_result",
        })

out = pd.DataFrame(rows)
OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(out.to_string(index=False))
