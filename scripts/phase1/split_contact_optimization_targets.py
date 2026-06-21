#!/usr/bin/env python
from pathlib import Path
import pandas as pd

SOFT_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_soft_selected_outputs")
IN = SOFT_OUT / "arctic5_contact_optimization_targets.csv"

penetration_out = SOFT_OUT / "arctic5_targets_penetration_refinement.csv"
repose_out = SOFT_OUT / "arctic5_targets_contact_repose.csv"
summary_out = SOFT_OUT / "arctic5_contact_optimization_target_summary.md"

df = pd.read_csv(IN)

penetration = df[df["target_type"] == "penetration_resolution_and_contact_refinement"]
repose = df[df["target_type"] == "contact_attraction_and_pose_reposition"]

penetration.to_csv(penetration_out, index=False)
repose.to_csv(repose_out, index=False)

with summary_out.open("w") as f:
    f.write("# ARCTIC-5 contact optimization target summary\n\n")
    f.write("## Target type counts\n\n")
    f.write(df.groupby("target_type").size().reset_index(name="count").to_markdown(index=False))
    f.write("\n\n## Penetration/contact refinement targets\n\n")
    f.write(penetration[["case", "source_method", "warning_tags"]].to_markdown(index=False))
    f.write("\n\n## Contact attraction / repose targets\n\n")
    f.write(repose[["case", "source_method", "warning_tags"]].to_markdown(index=False))
    f.write("\n")

print("[OK] wrote", penetration_out)
print("[OK] wrote", repose_out)
print("[OK] wrote", summary_out)
print(df[["case", "source_method", "target_type"]].to_string(index=False))
