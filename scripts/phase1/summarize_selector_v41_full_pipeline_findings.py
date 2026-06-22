#!/usr/bin/env python
from pathlib import Path
import pandas as pd

PERF_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance")
DOC_OUT = Path("docs/phase1/step3_full_pipeline_integration")
DOC_OUT.mkdir(parents=True, exist_ok=True)

combined = pd.read_csv(PERF_OUT / "arctic5_selector_combined_performance.csv")
rel = pd.read_csv(PERF_OUT / "arctic5_relative_pose_comparison_table.csv")

methods = [
    "default_baseline",
    "old_gpt55_selector_v1",
    "partaware_v2_attempt0",
    "selector_v41_refined_pipeline",
]

summary_rows = []

for case in sorted(combined["case"].unique()):
    sub = combined[combined["case"] == case].copy()

    def val(method, col):
        r = sub[sub["method"] == method]
        if r.empty or col not in r.columns:
            return None
        return float(r.iloc[0][col])

    best_cd = sub.sort_values("object_cd_mm").iloc[0]["method"]
    best_f10 = sub.sort_values("object_f10", ascending=False).iloc[0]["method"]
    best_contact = sub.sort_values("contact_p5_mm").iloc[0]["method"]

    rel_row = rel[rel["case"] == case].iloc[0]
    rel_v41_delta = rel_row.get("delta_selector_v41_refined_pipeline_minus_baseline", None)

    summary_rows.append({
        "case": case,
        "best_object_cd_method": best_cd,
        "best_object_f10_method": best_f10,
        "best_contact_p5_method": best_contact,
        "selector_v41_cd": val("selector_v41_refined_pipeline", "object_cd_mm"),
        "selector_v41_f10": val("selector_v41_refined_pipeline", "object_f10"),
        "selector_v41_contact_p5": val("selector_v41_refined_pipeline", "contact_p5_mm"),
        "selector_v41_relative_pose_delta_vs_baseline_mm": rel_v41_delta,
        "main_read": "",
    })

summary = pd.DataFrame(summary_rows)

def main_read(row):
    case = row["case"]
    if case == "aket01":
        return "positive case: best contact/F-score but penetration remains"
    if case == "abox01":
        return "object shape improves, but hand remains inside box"
    if case == "ascis01":
        return "thin object still hard; contact improves but still floating"
    if case == "alapuse01":
        return "visual pose may help, but GT/relative metrics worsen"
    if case == "amicuse01":
        return "articulated microwave remains fragmented / poorly aligned"
    return ""

summary["main_read"] = summary.apply(main_read, axis=1)

csv_out = DOC_OUT / "selector_v41_full_pipeline_findings_summary.csv"
md_out = DOC_OUT / "selector_v41_full_pipeline_findings_summary.md"

summary.to_csv(csv_out, index=False)

with md_out.open("w") as f:
    f.write("# selector-v4.1 full-pipeline findings summary\n\n")
    f.write("## Case-level summary\n\n")
    f.write(summary.to_markdown(index=False))
    f.write("\n\n## Main conclusion\n\n")
    f.write(
        "The selector-v4.1 refined-prompt pipeline is a successful full-pipeline integration, "
        "but it is not yet a consistent final-HOI improvement. It improves selected cases, "
        "especially aket01, while articulated and thin-object cases still require part-aware "
        "reconstruction and contact-aware optimization.\n"
    )

print("[OK] wrote", csv_out)
print("[OK] wrote", md_out)
print(summary.to_string(index=False))
