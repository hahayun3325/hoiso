from pathlib import Path
import pandas as pd

P = Path.home() / "foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases_surface/arctic_selected_cases_surface_paperstyle_metrics.csv"
OUT = Path.home() / "foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases_surface/arctic_surface_metric_deltas.md"

df = pd.read_csv(P)
ok = df[df["status"] == "ok"].copy()

pivot = ok.pivot(index="case", columns="method", values=["object_cd_mm", "object_f5", "object_f10"])
rows = []

for case in pivot.index:
    cd_default = pivot.loc[case, ("object_cd_mm", "default")]
    cd_selector = pivot.loc[case, ("object_cd_mm", "gpt55_selector")]
    f5_default = pivot.loc[case, ("object_f5", "default")]
    f5_selector = pivot.loc[case, ("object_f5", "gpt55_selector")]
    f10_default = pivot.loc[case, ("object_f10", "default")]
    f10_selector = pivot.loc[case, ("object_f10", "gpt55_selector")]

    rows.append({
        "case": case,
        "cd_default_mm": cd_default,
        "cd_selector_mm": cd_selector,
        "cd_delta_selector_minus_default_mm": cd_selector - cd_default,
        "cd_relative_change_%": 100.0 * (cd_selector - cd_default) / cd_default,
        "f5_delta": f5_selector - f5_default,
        "f10_delta": f10_selector - f10_default,
    })

delta = pd.DataFrame(rows)

avg = ok.groupby("method")[["object_cd_mm", "object_f5", "object_f10"]].mean()
cd_default = avg.loc["default", "object_cd_mm"]
cd_selector = avg.loc["gpt55_selector", "object_cd_mm"]

text = (
    "# ARCTIC Surface Metric Deltas\n\n"
    "Negative CD delta means selector is better.\n\n"
    "## Per-case deltas\n\n"
    + delta.to_markdown(index=False, floatfmt=".4f")
    + "\n\n## Average summary\n\n"
    f"- Default mean CD: {cd_default:.4f} mm\n"
    f"- Selector mean CD: {cd_selector:.4f} mm\n"
    f"- Mean CD improvement: {cd_default - cd_selector:.4f} mm\n"
    f"- Relative CD improvement: {(cd_default - cd_selector) / cd_default * 100.0:.2f}%\n"
)

OUT.write_text(text)
print(text)
print("[OK] wrote", OUT)
