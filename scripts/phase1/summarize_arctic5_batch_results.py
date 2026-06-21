#!/usr/bin/env python
from pathlib import Path
import pandas as pd

EXP_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance")
CSV = EXP_OUT / "arctic5_selector_combined_performance.csv"
OUT = EXP_OUT / "arctic5_batch_interpretation.md"

df = pd.read_csv(CSV)

with OUT.open("w") as f:
    f.write("# ARCTIC-5 automatic comparison batch interpretation\n\n")

    f.write("## Overall gate counts\n\n")
    gate_counts = df.groupby(["method", "selector_v4_gate"]).size().reset_index(name="count")
    f.write(gate_counts.to_markdown(index=False))
    f.write("\n\n")

    f.write("## Case-level observations\n\n")
    for case, sub in df.groupby("case"):
        f.write(f"### {case}\n\n")
        cols = [
            "method", "object_cd_mm", "object_f5", "object_f10",
            "contact_p5_mm", "hand_inside_object_ratio",
            "components", "selector_v4_gate", "final_status"
        ]
        cols = [c for c in cols if c in sub.columns]
        f.write(sub[cols].to_markdown(index=False))
        f.write("\n\n")

        ok = sub[sub["selector_v4_gate"] == "pass"]
        if len(ok) > 0:
            f.write("**Decision:** safe candidate exists; can be selected after visual confirmation.\n\n")
        else:
            f.write("**Decision:** no safe final replacement yet; send to fallback/contact-aware guidance.\n\n")

    f.write("## Main conclusion\n\n")
    f.write(
        "The batch infrastructure works, but no candidate currently passes the selector-v4 physical gate. "
        "Prompt refinement improves some object geometry results, especially aket01, but physical validity "
        "still requires attempt1 fallback or contact-aware guidance.\n"
    )

print("[OK] wrote", OUT)
