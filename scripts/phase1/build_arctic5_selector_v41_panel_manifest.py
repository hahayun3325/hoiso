#!/usr/bin/env python
from pathlib import Path
import pandas as pd

PERF_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance")
PANEL_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_v41_panels")

PHYS = PERF_OUT / "arctic5_selector_physical_metrics.csv"
GT = PERF_OUT / "arctic5_selector_gt_metrics.csv"
DEC = PERF_OUT / "selector_v4_1_soft_gate_decisions.csv"

OUT = PANEL_OUT / "arctic5_selector_v41_panel_manifest.csv"

phys = pd.read_csv(PHYS)
gt = pd.read_csv(GT)
dec = pd.read_csv(DEC)

df = phys.merge(
    gt[["case", "method", "run_id", "object_cd_mm", "object_f5", "object_f10", "hand_cd_mm"]],
    on=["case", "method", "run_id"],
    how="left",
)

df = df.merge(
    dec[["case", "chosen_method", "chosen_run_id", "decision", "warning_tags"]],
    on="case",
    how="left",
)

df["is_v41_selected"] = (
    (df["method"] == df["chosen_method"])
    & (df["run_id"] == df["chosen_run_id"])
)

df["input_image"] = df["input_image"].fillna("")

keep = [
    "case", "method", "run_id", "is_v41_selected",
    "decision", "warning_tags",
    "input_image", "hand_mesh", "object_mesh",
    "object_cd_mm", "object_f5", "object_f10",
    "contact_p5_mm", "hand_inside_object_ratio",
    "components", "largest_component_fraction",
    "selector_v4_gate",
]

PANEL_OUT.mkdir(parents=True, exist_ok=True)
df[keep].to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(df[["case", "method", "is_v41_selected", "object_cd_mm", "contact_p5_mm", "selector_v4_gate"]].to_string(index=False))
