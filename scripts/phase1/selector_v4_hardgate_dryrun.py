#!/usr/bin/env python
from pathlib import Path
import numpy as np
import pandas as pd

PHASE1 = Path("/home/fredcui/foho_phase0/phase1_diagnostics")

contact = pd.read_csv(PHASE1 / "first_contact_metrics/contact_metrics_summary_labeled.csv")
pen = pd.read_csv(PHASE1 / "penetration_diagnostics/penetration_diagnostics_summary.csv")
integ = pd.read_csv(PHASE1 / "object_integrity_metrics/object_integrity_summary.csv")

df = contact.merge(
    pen[[
        "sample_id",
        "object_inside_hand_ratio",
        "object_inside_hand_max_depth_mm",
        "hand_inside_object_ratio",
        "hand_inside_object_max_depth_mm",
    ]],
    on="sample_id",
    how="left",
)

df = df.merge(
    integ[[
        "sample_id",
        "num_components",
        "largest_component_face_ratio",
        "bbox_diag_mm",
        "is_watertight",
    ]],
    on="sample_id",
    how="left",
)

# Hard gates
df["severe_floating"] = (
    (df["floating"] == True)
    & (df["p5_hand_object_dist_mm"] > 20)
)

df["severe_penetration"] = (
    (df["object_inside_hand_ratio"].fillna(0) > 0.03)
    | (df["hand_inside_object_ratio"].fillna(0) > 0.20)
    | (df["object_inside_hand_max_depth_mm"].fillna(0) > 10)
    | (df["hand_inside_object_max_depth_mm"].fillna(0) > 10)
)

df["severe_fragmentation"] = (
    (df["num_components"].fillna(1) > 100)
    & (df["largest_component_face_ratio"].fillna(1) < 0.70)
)

df["oversized_object"] = df["bbox_diag_mm"].fillna(0) > 700

df["low_integrity"] = df["largest_component_face_ratio"].fillna(1) < 0.65

df["hard_fail_count"] = df[[
    "severe_floating",
    "severe_penetration",
    "severe_fragmentation",
    "oversized_object",
    "low_integrity",
]].sum(axis=1)

# Soft score only used after hard gates
df["soft_score"] = (
    -df["p5_hand_object_dist_mm"]
    -40.0 * df["object_inside_hand_ratio"].fillna(0)
    -40.0 * df["hand_inside_object_ratio"].fillna(0)
    -10.0 * np.clip((df["num_components"].fillna(1) - 1) / 100.0, 0, 1)
    +20.0 * df["largest_component_face_ratio"].fillna(0)
)

df["selector_v4_score"] = (
    -1000.0 * df["hard_fail_count"]
    + df["soft_score"]
)

def failure_reason(row):
    reasons = []
    for k in [
        "severe_floating",
        "severe_penetration",
        "severe_fragmentation",
        "oversized_object",
        "low_integrity",
    ]:
        if bool(row[k]):
            reasons.append(k)
    return "|".join(reasons) if reasons else "valid"

df["failure_reason"] = df.apply(failure_reason, axis=1)

out_dir = PHASE1 / "selector_v4_hardgate"
out_dir.mkdir(parents=True, exist_ok=True)

df.to_csv(out_dir / "selector_v4_candidate_scores.csv", index=False)

selected_rows = []
for case, g in df.groupby("case"):
    best = g.sort_values("selector_v4_score", ascending=False).iloc[0].copy()

    if (g["hard_fail_count"] == 0).any():
        best["final_decision"] = "select"
    else:
        best["final_decision"] = "reject_both_or_rerun"

    selected_rows.append(best)

selected = pd.DataFrame(selected_rows)
selected.to_csv(out_dir / "selector_v4_selected_cases.csv", index=False)

summary = selected.groupby("final_decision").size().reset_index(name="count")
summary.to_csv(out_dir / "selector_v4_summary.csv", index=False)

print("[Selected]")
print(selected[[
    "case", "sample_id", "method",
    "final_decision",
    "failure_reason",
    "hard_fail_count",
    "p5_hand_object_dist_mm",
    "floating",
    "object_inside_hand_ratio",
    "hand_inside_object_ratio",
    "num_components",
    "largest_component_face_ratio",
    "bbox_diag_mm",
]].to_string(index=False))

print("\n[Summary]")
print(summary.to_string(index=False))
