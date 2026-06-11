from pathlib import Path
import pandas as pd

DRY = Path.home() / "foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases/arctic_selected_cases_dryrun_metrics.csv"
SURF = Path.home() / "foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases_surface/arctic_selected_cases_surface_paperstyle_metrics.csv"
OUT = Path.home() / "foho_phase0/inspection/arctic_phase017/paper_style_eval_selected_cases_surface/dryrun_vs_surface_comparison.md"

dry = pd.read_csv(DRY)
surf = pd.read_csv(SURF)

dry = dry[dry["status"] == "ok"][["case", "method", "object_cd_mm", "object_f5", "object_f10"]]
surf = surf[surf["status"] == "ok"][["case", "method", "object_cd_mm", "object_f5", "object_f10"]]

m = dry.merge(surf, on=["case", "method"], suffixes=("_dry_vertex", "_surface"))

avg_dry = dry.groupby("method")[["object_cd_mm", "object_f5", "object_f10"]].mean()
avg_surf = surf.groupby("method")[["object_cd_mm", "object_f5", "object_f10"]].mean()

text = (
    "# ARCTIC Dry-Run vs Surface-Sampled Metric Comparison\n\n"
    "Dry-run uses raw mesh vertices. Surface-sampled evaluation uses uniformly sampled surface points.\n\n"
    "## Per-case comparison\n\n"
    + m.to_markdown(index=False)
    + "\n\n## Dry-run averages\n\n"
    + avg_dry.to_markdown()
    + "\n\n## Surface-sampled averages\n\n"
    + avg_surf.to_markdown()
    + "\n"
)

OUT.write_text(text)
print(text)
print("[OK] wrote", OUT)
