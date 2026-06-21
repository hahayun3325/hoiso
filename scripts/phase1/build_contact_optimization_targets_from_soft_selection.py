#!/usr/bin/env python
from pathlib import Path
import pandas as pd

SOFT_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_soft_selected_outputs")
IN = SOFT_OUT / "arctic5_soft_selected_manifest.csv"
OUT = SOFT_OUT / "arctic5_contact_optimization_targets.csv"

df = pd.read_csv(IN)

rows = []
for _, r in df.iterrows():
    tags = str(r.get("warning_tags", ""))

    if "floating_warning" in tags:
        target_type = "contact_attraction_and_pose_reposition"
    elif "penetration" in tags or "inside" in tags:
        target_type = "penetration_resolution_and_contact_refinement"
    else:
        target_type = "light_contact_refinement"

    rows.append({
        "case": r["case"],
        "source_method": r["method"],
        "source_run_id": r["run_id"],
        "hand_mesh": r["soft_selected_hand"],
        "object_mesh": r["soft_selected_object"],
        "warning_tags": tags,
        "target_type": target_type,
        "next_module": "contact_aware_optimization",
    })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(out.to_string(index=False))
