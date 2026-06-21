#!/usr/bin/env python
from pathlib import Path
import json
import os
import pandas as pd

EXP_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance")
SOFT_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_soft_selected_outputs")

DECISIONS = EXP_OUT / "selector_v4_1_soft_gate_decisions.csv"
PHYSICAL = EXP_OUT / "arctic5_selector_physical_metrics.csv"

dec = pd.read_csv(DECISIONS)
phys = pd.read_csv(PHYSICAL)

SOFT_OUT.mkdir(parents=True, exist_ok=True)

rows = []

for _, d in dec.iterrows():
    case = d["case"]
    method = d["chosen_method"]
    run_id = d["chosen_run_id"]

    match = phys[
        (phys["case"] == case)
        & (phys["method"] == method)
        & (phys["run_id"] == run_id)
    ]

    if match.empty:
        rows.append({
            "case": case,
            "status": "missing_selected_source",
            "method": method,
            "run_id": run_id,
        })
        continue

    src = match.iloc[0]
    hand = Path(src["hand_mesh"])
    obj = Path(src["object_mesh"])

    case_dir = SOFT_OUT / case
    case_dir.mkdir(parents=True, exist_ok=True)

    dst_hand = case_dir / "pred_hand_selected.ply"
    dst_obj = case_dir / "pred_object_selected.ply"
    decision_json = case_dir / "selector_v4_1_decision.json"

    for p in [dst_hand, dst_obj]:
        if p.exists() or p.is_symlink():
            p.unlink()

    os.symlink(hand.resolve(), dst_hand)
    os.symlink(obj.resolve(), dst_obj)

    decision = {
        "case": case,
        "decision": d["decision"],
        "chosen_method": method,
        "chosen_run_id": run_id,
        "warning_tags": d.get("warning_tags", ""),
        "soft_score": float(d["soft_score"]),
        "object_cd_mm": float(d["object_cd_mm"]),
        "object_f10": float(d["object_f10"]),
        "contact_p5_mm": float(d["contact_p5_mm"]),
        "hand_inside_object_ratio": float(d["hand_inside_object_ratio"]),
        "components": int(d["components"]),
        "largest_component_fraction": float(d["largest_component_fraction"]),
        "source_hand": str(hand),
        "source_object": str(obj),
        "soft_selected_hand": str(dst_hand),
        "soft_selected_object": str(dst_obj),
        "next_stage": "contact_aware_optimization",
        "is_final_physical_output": False,
    }

    decision_json.write_text(json.dumps(decision, indent=2))

    rows.append({
        "case": case,
        "status": "soft_selected",
        "method": method,
        "run_id": run_id,
        "warning_tags": d.get("warning_tags", ""),
        "soft_selected_hand": str(dst_hand),
        "soft_selected_object": str(dst_obj),
        "next_stage": "contact_aware_optimization",
        "is_final_physical_output": False,
    })

out = pd.DataFrame(rows)
out_csv = SOFT_OUT / "arctic5_soft_selected_manifest.csv"
out.to_csv(out_csv, index=False)

print("[OK] wrote", out_csv)
print(out.to_string(index=False))
