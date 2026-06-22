#!/usr/bin/env python
from pathlib import Path
import pandas as pd

REPORT_OUT = Path("/home/fredcui/foho_phase0/phase1_report_assets")
TABLE_OUT = REPORT_OUT / "tables"
TABLE_OUT.mkdir(parents=True, exist_ok=True)

PERF_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance")

combined = pd.read_csv(PERF_OUT / "arctic5_selector_combined_performance.csv")
rel_wide = pd.read_csv(PERF_OUT / "arctic5_relative_pose_comparison_table.csv")

v41 = combined[combined["method"] == "selector_v41_refined_pipeline"].copy()

v41 = v41.merge(
    rel_wide[[
        "case",
        "selector_v41_refined_pipeline",
        "delta_selector_v41_refined_pipeline_minus_baseline",
    ]].rename(columns={
        "selector_v41_refined_pipeline": "relative_object_center_error_mm",
        "delta_selector_v41_refined_pipeline_minus_baseline": "relative_pose_delta_vs_baseline_mm",
    }),
    on="case",
    how="left",
)

case_read = {
    "abox01": "Object shape improves, but hand remains inside box.",
    "aket01": "Best positive case: contact and F-score improve, but penetration remains.",
    "alapuse01": "Visual pose may look meaningful, but GT and relative metrics worsen.",
    "amicuse01": "Microwave remains fragmented / poorly aligned; articulated case is hard.",
    "ascis01": "Thin scissors remain hard; contact improves but object still floats.",
}

v41["main_read"] = v41["case"].map(case_read)

keep = [
    "case",
    "object_cd_mm",
    "object_f10",
    "contact_p5_mm",
    "hand_inside_object_ratio",
    "largest_component_fraction",
    "relative_object_center_error_mm",
    "relative_pose_delta_vs_baseline_mm",
    "selector_v4_gate",
    "main_read",
]

table = v41[keep].copy()

# Round numeric values.
for c in table.columns:
    if table[c].dtype.kind in "fc":
        table[c] = table[c].round(3)

summary_md = TABLE_OUT / "arctic5_v41_rerun_summary.md"
with summary_md.open("w") as f:
    f.write("# ARCTIC-5 selector-v4.1 full-pipeline rerun summary\n\n")
    f.write(table.to_markdown(index=False))
    f.write("\n\n")
    f.write("## Main conclusion\n\n")
    f.write(
        "Selector-v4.1 full-pipeline rerun is technically successful and gives partial improvements, "
        "especially on `aket01`. However, it does not consistently improve all ARCTIC-5 cases. "
        "The remaining failures motivate part-wise object reconstruction and contact-aware optimization.\n"
    )

avg_cols = ["object_cd_mm", "object_f10", "contact_p5_mm", "hand_inside_object_ratio"]
avg = combined.groupby("method")[avg_cols].mean(numeric_only=True).round(3).reset_index()

avg_md = TABLE_OUT / "arctic5_method_average_summary.md"
with avg_md.open("w") as f:
    f.write("# ARCTIC-5 method average summary\n\n")
    f.write(avg.to_markdown(index=False))
    f.write("\n\n")
    f.write("Lower is better for `object_cd_mm`, `contact_p5_mm`, and `hand_inside_object_ratio`; higher is better for `object_f10`.\n")

print("[OK] wrote", summary_md)
print("[OK] wrote", avg_md)
print(table.to_markdown(index=False))
