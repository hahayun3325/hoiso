#!/usr/bin/env python
from pathlib import Path
import pandas as pd
import numpy as np

phase1 = Path("/home/fredcui/foho_phase0/phase1_diagnostics")

contact = pd.read_csv(phase1 / "first_contact_metrics/contact_metrics_summary_labeled.csv")
penetration = pd.read_csv(phase1 / "penetration_diagnostics/penetration_diagnostics_summary.csv")

df = contact.merge(
    penetration[[
        "sample_id",
        "object_inside_hand_ratio",
        "object_inside_hand_max_depth_mm",
    ]],
    on="sample_id",
    how="left"
)

# Lower is better for distance / floating / penetration.
df["score_contact"] = -df["p5_hand_object_dist_mm"]
df["score_floating"] = np.where(df["floating"], -100.0, 0.0)
df["score_penetration"] = -50.0 * df["object_inside_hand_ratio"].fillna(0.0)
df["score_heavy_contact_warning"] = np.where(
    df["contact_status_label"].eq("heavy_contact_check_penetration"),
    -20.0,
    0.0,
)

df["selector_v2_score"] = (
    df["score_contact"]
    + df["score_floating"]
    + df["score_penetration"]
    + df["score_heavy_contact_warning"]
)

out = phase1 / "selector_v2_dryrun"
out.mkdir(parents=True, exist_ok=True)

df.to_csv(out / "selector_v2_candidate_scores.csv", index=False)

best = (
    df.sort_values("selector_v2_score", ascending=False)
      .groupby("case", as_index=False)
      .head(1)
)

best.to_csv(out / "selector_v2_selected_cases.csv", index=False)

print("[OK] wrote", out / "selector_v2_candidate_scores.csv")
print("[OK] wrote", out / "selector_v2_selected_cases.csv")
print(best[[
    "case",
    "sample_id",
    "method",
    "selector_v2_score",
    "p5_hand_object_dist_mm",
    "floating",
    "object_inside_hand_ratio",
    "contact_status_label",
]].to_string(index=False))
