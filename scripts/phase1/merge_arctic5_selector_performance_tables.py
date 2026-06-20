#!/usr/bin/env python
from pathlib import Path
import pandas as pd

EXP_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance")

GT = EXP_OUT / "arctic5_selector_gt_metrics.csv"
PHYSICAL = EXP_OUT / "arctic5_selector_physical_metrics.csv"
OUT = EXP_OUT / "arctic5_selector_combined_performance.csv"
SUMMARY = EXP_OUT / "arctic5_selector_combined_summary.md"

gt = pd.read_csv(GT)
phys = pd.read_csv(PHYSICAL)

print("[GT columns]", list(gt.columns))
print("[PHYSICAL columns]", list(phys.columns))

keys = ["case", "method", "run_id"]

merged = phys.merge(
    gt,
    on=keys,
    how="left",
    suffixes=("_physical", "_gt")
)

# Decide final status from the physical gate.
def final_status(row):
    gate = row.get("selector_v4_gate")
    if gate == "pass":
        return "accepted_by_selector_v4"
    if gate == "warning_low_integrity":
        return "selected_with_warning"
    if gate == "missing_mesh":
        return "missing_rerun"
    if isinstance(gate, str) and gate.startswith("reject"):
        return "rejected_by_selector_v4"
    return "unknown"

merged["final_status"] = merged.apply(final_status, axis=1)

keep_cols = [
    "case",
    "method",
    "run_id",
    "exists_physical",
    "status_gt",
    "object_cd_mm",
    "object_f5",
    "object_f10",
    "hand_cd_mm",
    "contact_p5_mm",
    "contact_mean_mm",
    "object_inside_hand_ratio",
    "object_inside_hand_max_depth_mm",
    "hand_inside_object_ratio",
    "hand_inside_object_max_depth_mm",
    "components",
    "largest_component_fraction",
    "bbox_diag_mm",
    "selector_v4_gate",
    "final_status",
]

keep_cols = [c for c in keep_cols if c in merged.columns]
table = merged[keep_cols].copy()

OUT.parent.mkdir(parents=True, exist_ok=True)
table.to_csv(OUT, index=False)

with SUMMARY.open("w") as f:
    f.write("# ARCTIC-5 selector combined performance summary\n\n")
    f.write("## Main table\n\n")
    f.write(table.to_markdown(index=False))
    f.write("\n\n## Average GT metrics by method\n\n")
    ok = table[table.get("status_gt", "") == "ok"] if "status_gt" in table.columns else table
    metric_cols = [c for c in ["object_cd_mm", "object_f5", "object_f10", "hand_cd_mm"] if c in table.columns]
    if metric_cols:
        f.write(ok.groupby("method")[metric_cols].mean().to_markdown())
    f.write("\n\n## Physical gate counts\n\n")
    f.write(table.groupby(["method", "selector_v4_gate"]).size().reset_index(name="count").to_markdown(index=False))
    f.write("\n")

print("[OK] wrote", OUT)
print("[OK] wrote", SUMMARY)
print(table.to_string(index=False))
