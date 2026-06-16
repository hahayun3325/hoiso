#!/usr/bin/env python
from pathlib import Path
import pandas as pd
import numpy as np

PHASE1 = Path("/home/fredcui/foho_phase0/phase1_diagnostics")

contact = pd.read_csv(PHASE1 / "first_contact_metrics/contact_metrics_summary_labeled.csv")
pen = pd.read_csv(PHASE1 / "penetration_diagnostics/penetration_diagnostics_summary.csv")
integ = pd.read_csv(PHASE1 / "object_integrity_metrics/object_integrity_summary.csv")

df0 = contact.merge(
    pen[[
        "sample_id",
        "object_inside_hand_ratio",
        "object_inside_hand_max_depth_mm",
        "hand_inside_object_ratio",
        "hand_inside_object_max_depth_mm",
    ]],
    on="sample_id",
    how="left",
).merge(
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

rows = []

for floating_p5_thr in [15, 20, 25, 30, 40]:
    df = df0.copy()

    df["severe_floating"] = (
        (df["floating"] == True)
        & (df["p5_hand_object_dist_mm"] > floating_p5_thr)
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

    df["soft_score"] = (
        -df["p5_hand_object_dist_mm"]
        -40.0 * df["object_inside_hand_ratio"].fillna(0)
        -40.0 * df["hand_inside_object_ratio"].fillna(0)
        -10.0 * np.clip((df["num_components"].fillna(1) - 1) / 100.0, 0, 1)
        +20.0 * df["largest_component_face_ratio"].fillna(0)
    )

    df["score"] = -1000 * df["hard_fail_count"] + df["soft_score"]

    selected = []
    for case, g in df.groupby("case"):
        best = g.sort_values("score", ascending=False).iloc[0].copy()
        best["floating_p5_threshold_mm"] = floating_p5_thr
        best["final_decision"] = "select" if (g["hard_fail_count"] == 0).any() else "reject_both_or_rerun"
        selected.append(best)

    selected = pd.DataFrame(selected)
    rows.append(selected)

out = pd.concat(rows, ignore_index=True)

out_dir = PHASE1 / "selector_v4_threshold_sweep"
out_dir.mkdir(parents=True, exist_ok=True)

out.to_csv(out_dir / "selector_v4_threshold_sweep_selected_cases.csv", index=False)

summary = out.groupby("floating_p5_threshold_mm").agg(
    selected_count=("final_decision", lambda x: (x == "select").sum()),
    reject_count=("final_decision", lambda x: (x == "reject_both_or_rerun").sum()),
).reset_index()

summary.to_csv(out_dir / "selector_v4_threshold_sweep_summary.csv", index=False)

print("[Summary]")
print(summary.to_string(index=False))

print("\n[Selected cases]")
print(out[[
    "floating_p5_threshold_mm",
    "case",
    "sample_id",
    "method",
    "final_decision",
    "hard_fail_count",
    "p5_hand_object_dist_mm",
    "floating",
    "object_inside_hand_ratio",
    "hand_inside_object_ratio",
    "num_components",
    "largest_component_face_ratio",
    "bbox_diag_mm",
]].to_string(index=False))
