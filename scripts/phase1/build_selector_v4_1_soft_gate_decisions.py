#!/usr/bin/env python
from pathlib import Path
import pandas as pd
import numpy as np

EXP_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance")
IN = EXP_OUT / "arctic5_selector_combined_performance.csv"
OUT = EXP_OUT / "selector_v4_1_soft_gate_decisions.csv"

df = pd.read_csv(IN)

def is_missing(row):
    return not bool(row.get("exists_physical", False)) or str(row.get("status_gt", "")) != "ok"

def hard_reject_reason(row):
    if is_missing(row):
        return "missing_or_invalid_prediction"

    lcf = row.get("largest_component_fraction", np.nan)
    comps = row.get("components", np.nan)
    p5 = row.get("contact_p5_mm", np.nan)
    hand_inside = row.get("hand_inside_object_ratio", np.nan)
    bbox = row.get("bbox_diag_mm", np.nan)

    # Extreme hard failures only.
    if pd.notna(hand_inside) and hand_inside >= 0.95:
        return "extreme_hand_trapped_inside_object"

    if pd.notna(p5) and p5 > 200:
        return "extreme_floating"

    if pd.notna(lcf) and lcf < 0.50:
        return "severe_low_integrity"

    if pd.notna(comps) and comps > 250:
        return "severe_fragmentation"

    if pd.notna(bbox) and bbox > 3500:
        return "extreme_oversized_object"

    return ""

def warning_tags(row):
    tags = []

    p5 = row.get("contact_p5_mm", np.nan)
    obj_in = row.get("object_inside_hand_ratio", np.nan)
    hand_in = row.get("hand_inside_object_ratio", np.nan)
    obj_depth = row.get("object_inside_hand_max_depth_mm", np.nan)
    hand_depth = row.get("hand_inside_object_max_depth_mm", np.nan)
    lcf = row.get("largest_component_fraction", np.nan)
    comps = row.get("components", np.nan)

    if pd.notna(p5) and p5 > 20:
        tags.append("floating_warning")
    if pd.notna(obj_in) and obj_in > 0.03:
        tags.append("object_inside_hand_warning")
    if pd.notna(hand_in) and hand_in > 0.20:
        tags.append("hand_inside_object_warning")
    if pd.notna(obj_depth) and obj_depth > 10:
        tags.append("object_penetration_depth_warning")
    if pd.notna(hand_depth) and hand_depth > 10:
        tags.append("hand_penetration_depth_warning")
    if pd.notna(lcf) and lcf < 0.70:
        tags.append("low_integrity_warning")
    if pd.notna(comps) and comps > 100:
        tags.append("fragmentation_warning")

    return ";".join(tags)

def score_candidate(row):
    # Lower is better.
    cd = row.get("object_cd_mm", np.nan)
    f10 = row.get("object_f10", np.nan)
    p5 = row.get("contact_p5_mm", np.nan)
    lcf = row.get("largest_component_fraction", np.nan)
    comps = row.get("components", np.nan)

    cd = 200.0 if pd.isna(cd) else float(cd)
    f10 = 0.0 if pd.isna(f10) else float(f10)
    p5 = 200.0 if pd.isna(p5) else float(p5)
    lcf = 0.5 if pd.isna(lcf) else float(lcf)
    comps = 200.0 if pd.isna(comps) else float(comps)

    # Object shape + contact proximity + integrity.
    # Penalize high CD, high floating distance, fragmentation, low LCF.
    # Reward F10.
    score = (
        cd
        + 0.50 * p5
        + 0.10 * comps
        + 50.0 * (1.0 - lcf)
        - 100.0 * f10
    )
    return float(score)

rows = []

for case, sub in df.groupby("case"):
    scored = []
    for _, row in sub.iterrows():
        row = row.copy()
        hard = hard_reject_reason(row)
        warn = warning_tags(row)
        score = score_candidate(row)

        if hard:
            label = "hard_reject"
        elif warn:
            label = "selected_for_contact_aware_optimization_candidate"
        else:
            label = "selected_clean_candidate"

        scored.append((score, label, hard, warn, row))

    valid = [x for x in scored if x[1] != "hard_reject"]

    if valid:
        valid.sort(key=lambda x: x[0])
        chosen_score, chosen_label, hard, warn, chosen = valid[0]
        decision = "selected_for_contact_aware_optimization" if warn else "selected_clean"
        rows.append({
            "case": case,
            "decision": decision,
            "chosen_method": chosen["method"],
            "chosen_run_id": chosen["run_id"],
            "soft_score": chosen_score,
            "warning_tags": warn,
            "hard_reject_reason": "",
            "object_cd_mm": chosen.get("object_cd_mm"),
            "object_f10": chosen.get("object_f10"),
            "contact_p5_mm": chosen.get("contact_p5_mm"),
            "hand_inside_object_ratio": chosen.get("hand_inside_object_ratio"),
            "components": chosen.get("components"),
            "largest_component_fraction": chosen.get("largest_component_fraction"),
        })
    else:
        scored.sort(key=lambda x: x[0])
        chosen_score, chosen_label, hard, warn, chosen = scored[0]
        rows.append({
            "case": case,
            "decision": "reject_and_rerun_or_manual_review",
            "chosen_method": "",
            "chosen_run_id": "",
            "soft_score": chosen_score,
            "warning_tags": warn,
            "hard_reject_reason": hard,
            "object_cd_mm": chosen.get("object_cd_mm"),
            "object_f10": chosen.get("object_f10"),
            "contact_p5_mm": chosen.get("contact_p5_mm"),
            "hand_inside_object_ratio": chosen.get("hand_inside_object_ratio"),
            "components": chosen.get("components"),
            "largest_component_fraction": chosen.get("largest_component_fraction"),
        })

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(out.to_string(index=False))
