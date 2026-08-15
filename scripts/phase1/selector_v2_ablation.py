#!/usr/bin/env python
from pathlib import Path
import numpy as np
import pandas as pd

phase1 = Path("/home/fredcui/foho_phase0/phase1_diagnostics")

contact = pd.read_csv(phase1 / "first_contact_metrics/contact_metrics_summary_labeled.csv")
pen = pd.read_csv(phase1 / "penetration_diagnostics/penetration_diagnostics_summary.csv")

df = contact.merge(
    pen[[
        "sample_id",
        "object_inside_hand_ratio",
        "object_inside_hand_max_depth_mm",
        "hand_inside_object_ratio",
        "hand_inside_object_max_depth_mm",
    ]],
    on="sample_id",
    how="left"
)

df["heavy"] = df["contact_status_label"].eq("heavy_contact_check_penetration").astype(float)
df["float_pen"] = df["floating"].astype(float)

def select_with(name, score):
    tmp = df.copy()
    tmp["ablation_name"] = name
    tmp["score"] = score(tmp)
    best = tmp.sort_values("score", ascending=False).groupby("case", as_index=False).head(1)
    return best

ablations = []

ablations.append(select_with(
    "contact_only",
    lambda x: -x["p5_hand_object_dist_mm"]
))

ablations.append(select_with(
    "contact_plus_floating",
    lambda x: -x["p5_hand_object_dist_mm"] - 100*x["float_pen"]
))

ablations.append(select_with(
    "contact_floating_penetration",
    lambda x: (
        -x["p5_hand_object_dist_mm"]
        -100*x["float_pen"]
        -60*x["object_inside_hand_ratio"].fillna(0)
        -60*x["hand_inside_object_ratio"].fillna(0)
        -20*x["heavy"]
    )
))

result = pd.concat(ablations, ignore_index=True)

out_dir = phase1 / "selector_v2_ablation"
out_dir.mkdir(parents=True, exist_ok=True)

result.to_csv(out_dir / "selector_v2_ablation_selected_cases.csv", index=False)

summary = result.groupby("ablation_name").agg(
    selected_floating_rate=("floating", "mean"),
    selected_mean_p5_mm=("p5_hand_object_dist_mm", "mean"),
    selected_mean_obj_inside_hand=("object_inside_hand_ratio", "mean"),
    selected_mean_hand_inside_obj=("hand_inside_object_ratio", "mean"),
).reset_index()

summary.to_csv(out_dir / "selector_v2_ablation_summary.csv", index=False)

print("[OK] selected cases")
print(result[[
    "ablation_name", "case", "sample_id", "method", "score",
    "p5_hand_object_dist_mm", "floating",
    "object_inside_hand_ratio", "hand_inside_object_ratio",
    "contact_status_label"
]].to_string(index=False))

print("\n[OK] summary")
print(summary.to_string(index=False))
