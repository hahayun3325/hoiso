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
        "small_component_count_faces_lt_10",
        "bbox_diag_mm",
        "is_watertight",
    ]],
    on="sample_id",
    how="left",
)

df["floating_penalty"] = df["floating"].astype(float)
df["heavy_contact_penalty"] = df["contact_status_label"].eq("heavy_contact_check_penetration").astype(float)

# Integrity penalties
df["fragmentation_penalty"] = np.clip((df["num_components"].fillna(1) - 1) / 20.0, 0, 1)
df["low_largest_component_penalty"] = 1.0 - df["largest_component_face_ratio"].fillna(0.0)

# Wrong-scale / oversized-object penalty: soft only for now.
df["oversize_penalty"] = (df["bbox_diag_mm"].fillna(0) > 700).astype(float)

def score_contact_only(x):
    return -x["p5_hand_object_dist_mm"]

def score_contact_floating(x):
    return (
        -x["p5_hand_object_dist_mm"]
        -100.0 * x["floating_penalty"]
    )

def score_contact_penetration(x):
    return (
        -x["p5_hand_object_dist_mm"]
        -100.0 * x["floating_penalty"]
        -80.0 * x["object_inside_hand_ratio"].fillna(0)
        -80.0 * x["hand_inside_object_ratio"].fillna(0)
        -20.0 * x["heavy_contact_penalty"]
    )

def score_full_v3(x):
    return (
        -x["p5_hand_object_dist_mm"]
        -100.0 * x["floating_penalty"]
        -80.0 * x["object_inside_hand_ratio"].fillna(0)
        -80.0 * x["hand_inside_object_ratio"].fillna(0)
        -20.0 * x["heavy_contact_penalty"]
        -30.0 * x["fragmentation_penalty"]
        -30.0 * x["low_largest_component_penalty"]
        -30.0 * x["oversize_penalty"]
    )

def select(name, score_fn):
    tmp = df.copy()
    tmp["ablation_name"] = name
    tmp["score"] = score_fn(tmp)

    best = (
        tmp.sort_values("score", ascending=False)
           .groupby("case", as_index=False)
           .head(1)
           .copy()
    )

    # Add final validity label.
    best["selected_status"] = "selected"
    best.loc[best["floating"], "selected_status"] = "selected_but_floating"
    best.loc[
        (best["object_inside_hand_ratio"].fillna(0) > 0.03)
        | (best["hand_inside_object_ratio"].fillna(0) > 0.20),
        "selected_status"
    ] = "selected_but_penetration_risk"
    best.loc[
        (best["floating"])
        & (best["p5_hand_object_dist_mm"] > 80),
        "selected_status"
    ] = "reject_both_or_rerun"

    return best

all_best = pd.concat([
    select("contact_only", score_contact_only),
    select("contact_plus_floating", score_contact_floating),
    select("contact_plus_penetration", score_contact_penetration),
    select("full_v3_contact_penetration_integrity", score_full_v3),
], ignore_index=True)

out_dir = PHASE1 / "selector_v3_ablation"
out_dir.mkdir(parents=True, exist_ok=True)

all_best.to_csv(out_dir / "selector_v3_ablation_selected_cases.csv", index=False)

summary = all_best.groupby("ablation_name").agg(
    selected_floating_rate=("floating", "mean"),
    selected_mean_p5_mm=("p5_hand_object_dist_mm", "mean"),
    selected_mean_obj_inside_hand=("object_inside_hand_ratio", "mean"),
    selected_mean_hand_inside_obj=("hand_inside_object_ratio", "mean"),
    selected_mean_components=("num_components", "mean"),
    selected_mean_largest_component_ratio=("largest_component_face_ratio", "mean"),
).reset_index()

summary.to_csv(out_dir / "selector_v3_ablation_summary.csv", index=False)

print("\n[Selected cases]")
print(all_best[[
    "ablation_name", "case", "sample_id", "method", "score",
    "p5_hand_object_dist_mm", "floating",
    "object_inside_hand_ratio", "hand_inside_object_ratio",
    "num_components", "largest_component_face_ratio",
    "selected_status"
]].to_string(index=False))

print("\n[Summary]")
print(summary.to_string(index=False))
