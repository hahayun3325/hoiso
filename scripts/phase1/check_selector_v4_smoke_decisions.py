#!/usr/bin/env python
from pathlib import Path
import pandas as pd
import json

phase1 = Path("/home/fredcui/foho_phase0/phase1_diagnostics")
smoke_csv = phase1 / "selector_v4_smoke/selector_v4_smoke_cases.csv"
selected_csv = phase1 / "selector_v4_pipeline_dryrun/selector_v4_pipeline_dryrun_selected_cases.csv"
out_dir = phase1 / "selector_v4_smoke"
out_dir.mkdir(parents=True, exist_ok=True)

smoke = pd.read_csv(smoke_csv)
selected = pd.read_csv(selected_csv)

rows = []
for _, r in smoke.iterrows():
    case = r["case"]
    exp = r["expected_decision"]
    hit = selected[selected["case"] == case]

    if len(hit) == 0:
        rows.append({
            "case": case,
            "expected_decision": exp,
            "actual_decision": "MISSING",
            "match": False,
            "notes": "case not found in selector output",
        })
        continue

    h = hit.iloc[0]
    actual = h["final_decision"]
    rows.append({
        "case": case,
        "expected_decision": exp,
        "actual_decision": actual,
        "match": actual == exp,
        "selected_sample_id": h["sample_id"],
        "method": h["method"],
        "p5_hand_object_dist_mm": h["p5_hand_object_dist_mm"],
        "floating": h["floating"],
        "object_inside_hand_ratio": h["object_inside_hand_ratio"],
        "hand_inside_object_ratio": h["hand_inside_object_ratio"],
        "failure_reasons": h.get("failure_reasons", ""),
    })

df = pd.DataFrame(rows)
out = out_dir / "selector_v4_smoke_decision_check.csv"
df.to_csv(out, index=False)

print("[OK] wrote", out)
print(df.to_string(index=False))

summary = {
    "num_cases": int(len(df)),
    "num_match": int(df["match"].sum()),
    "all_match": bool(df["match"].all()),
}
(out_dir / "selector_v4_smoke_summary.json").write_text(json.dumps(summary, indent=2))
print(summary)
