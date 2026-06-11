from pathlib import Path
import pandas as pd

HOME = Path.home()
REPORT_DIR = HOME / "foho_phase0/inspection/arctic_phase017/final_report_assets"
CSV = REPORT_DIR / "arctic_selected_paper_like_metrics_surface.csv"
OUT = REPORT_DIR / "arctic_selected_paper_like_metrics_report_table.md"

df = pd.read_csv(CSV)

# Per-case table.
case_table = df[[
    "case",
    "label",
    "object_cd_mm",
    "f5",
    "f10",
    "pred_obj_components",
    "pred_obj_fragmentation",
    "hand_align_cd_mm",
    "sim_scale",
]].copy()

case_table["object_cd_mm"] = case_table["object_cd_mm"].round(2)
case_table["f5"] = case_table["f5"].round(4)
case_table["f10"] = case_table["f10"].round(4)
case_table["pred_obj_fragmentation"] = case_table["pred_obj_fragmentation"].round(4)
case_table["hand_align_cd_mm"] = case_table["hand_align_cd_mm"].round(2)
case_table["sim_scale"] = case_table["sim_scale"].round(4)

# Method average table.
avg = df.groupby("label")[[
    "object_cd_mm",
    "f5",
    "f10",
    "hand_align_cd_mm",
]].mean().reset_index()

avg["object_cd_mm"] = avg["object_cd_mm"].round(2)
avg["f5"] = avg["f5"].round(4)
avg["f10"] = avg["f10"].round(4)
avg["hand_align_cd_mm"] = avg["hand_align_cd_mm"].round(2)

# Delta table.
piv = df.pivot(index="case", columns="label", values=["object_cd_mm", "f5", "f10"])
delta_rows = []

for case in piv.index:
    b_cd = piv.loc[case, ("object_cd_mm", "baseline")]
    s_cd = piv.loc[case, ("object_cd_mm", "gpt55_selector")]
    b_f5 = piv.loc[case, ("f5", "baseline")]
    s_f5 = piv.loc[case, ("f5", "gpt55_selector")]
    b_f10 = piv.loc[case, ("f10", "baseline")]
    s_f10 = piv.loc[case, ("f10", "gpt55_selector")]

    delta_rows.append({
        "case": case,
        "cd_delta_selector_minus_baseline_mm": round(s_cd - b_cd, 2),
        "cd_relative_change_%": round((s_cd - b_cd) / b_cd * 100.0, 2),
        "f5_delta": round(s_f5 - b_f5, 4),
        "f10_delta": round(s_f10 - b_f10, 4),
    })

delta = pd.DataFrame(delta_rows)

text = (
    "# ARCTIC Selected-Case Paper-Like Metrics\n\n"
    "Scope: five manually selected ARCTIC Phase 0.17 cases. This is selected-case paper-style evaluation, not the official full ARCTIC benchmark.\n\n"
    "## Method averages\n\n"
    + avg.to_markdown(index=False)
    + "\n\n## Per-case metrics\n\n"
    + case_table.to_markdown(index=False)
    + "\n\n## Per-case selector deltas\n\n"
    + delta.to_markdown(index=False)
    + "\n\nNegative CD delta means the selector is better.\n"
)

OUT.write_text(text)
print(text)
print("[OK] wrote", OUT)
