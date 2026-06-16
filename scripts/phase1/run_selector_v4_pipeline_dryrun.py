#!/usr/bin/env python
from pathlib import Path
import json
import yaml
import pandas as pd
import numpy as np

cfg_path = Path("configs/phase1_selector_v4_implementation.yaml")
cfg = yaml.safe_load(cfg_path.read_text())["selector_v4"]

out_dir = Path(cfg["paths"]["decision_output_dir"])
out_dir.mkdir(parents=True, exist_ok=True)

contact = pd.read_csv(cfg["diagnostics"]["contact_summary_csv"])
pen = pd.read_csv(cfg["diagnostics"]["penetration_summary_csv"])
integ = pd.read_csv(cfg["diagnostics"]["object_integrity_csv"])

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

hg = cfg["hard_gates"]

df["severe_floating"] = (
    (df["floating"] == True)
    & (df["p5_hand_object_dist_mm"] > hg["severe_floating"]["p5_threshold_mm"])
)

df["borderline_floating"] = (
    (df["floating"] == True)
    & (df["p5_hand_object_dist_mm"] > hg["severe_floating"]["borderline_p5_threshold_mm"])
)

df["severe_penetration"] = (
    (df["object_inside_hand_ratio"].fillna(0) > hg["severe_penetration"]["object_inside_hand_ratio"])
    | (df["hand_inside_object_ratio"].fillna(0) > hg["severe_penetration"]["hand_inside_object_ratio"])
    | (df["object_inside_hand_max_depth_mm"].fillna(0) > hg["severe_penetration"]["object_inside_hand_max_depth_mm"])
    | (df["hand_inside_object_max_depth_mm"].fillna(0) > hg["severe_penetration"]["hand_inside_object_max_depth_mm"])
)

df["severe_fragmentation"] = (
    (df["num_components"].fillna(1) > hg["object_integrity"]["severe_fragmentation_num_components"])
    & (df["largest_component_face_ratio"].fillna(1) < hg["object_integrity"]["severe_fragmentation_largest_component_ratio"])
)

df["low_integrity"] = (
    df["largest_component_face_ratio"].fillna(1)
    < hg["object_integrity"]["low_integrity_largest_component_ratio"]
)

df["oversized_object"] = (
    df["bbox_diag_mm"].fillna(0)
    > hg["object_integrity"]["oversized_bbox_diag_mm"]
)

fail_cols = [
    "severe_floating",
    "severe_penetration",
    "severe_fragmentation",
    "low_integrity",
    "oversized_object",
]

df["hard_fail_count"] = df[fail_cols].sum(axis=1)

df["soft_score"] = (
    -df["p5_hand_object_dist_mm"]
    -40.0 * df["object_inside_hand_ratio"].fillna(0)
    -40.0 * df["hand_inside_object_ratio"].fillna(0)
    -10.0 * np.clip((df["num_components"].fillna(1) - 1) / 100.0, 0, 1)
    +20.0 * df["largest_component_face_ratio"].fillna(0)
)

df["selector_v4_score"] = -1000.0 * df["hard_fail_count"] + df["soft_score"]

def reasons(row):
    r = [c for c in fail_cols if bool(row[c])]
    return r if r else ["valid"]

df["failure_reasons"] = df.apply(reasons, axis=1)

selected_rows = []

for case, g in df.groupby("case"):
    if (g["hard_fail_count"] == 0).any():
        valid = g[g["hard_fail_count"] == 0]
        best = valid.sort_values("selector_v4_score", ascending=False).iloc[0].copy()
        decision = "select"
    else:
        best = g.sort_values("selector_v4_score", ascending=False).iloc[0].copy()
        decision = "reject_both_or_rerun"

    best["final_decision"] = decision
    selected_rows.append(best)

    decision_json = {
        "case": case,
        "selected_sample_id": best["sample_id"],
        "selected_method": best["method"],
        "final_decision": decision,
        "failure_reasons": best["failure_reasons"],
        "selector_v4_score": float(best["selector_v4_score"]),
        "metrics": {
            "p5_hand_object_dist_mm": float(best["p5_hand_object_dist_mm"]),
            "floating": bool(best["floating"]),
            "object_inside_hand_ratio": float(best["object_inside_hand_ratio"]),
            "hand_inside_object_ratio": float(best["hand_inside_object_ratio"]),
            "num_components": int(best["num_components"]),
            "largest_component_face_ratio": float(best["largest_component_face_ratio"]),
            "bbox_diag_mm": float(best["bbox_diag_mm"]),
        },
        "mode": cfg["mode"],
    }

    (out_dir / f"{case}_selector_v4_decision.json").write_text(
        json.dumps(decision_json, indent=2)
    )

selected = pd.DataFrame(selected_rows)
selected.to_csv(out_dir / "selector_v4_pipeline_dryrun_selected_cases.csv", index=False)
df.to_csv(out_dir / "selector_v4_pipeline_dryrun_candidate_scores.csv", index=False)

print("[OK] wrote decisions to", out_dir)
print(selected[[
    "case", "sample_id", "method", "final_decision",
    "failure_reasons", "p5_hand_object_dist_mm",
    "floating", "object_inside_hand_ratio", "hand_inside_object_ratio",
    "num_components", "largest_component_face_ratio", "bbox_diag_mm"
]].to_string(index=False))
