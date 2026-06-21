#!/usr/bin/env python
from pathlib import Path
import pandas as pd
import json

PHASE0 = Path("/home/fredcui/foho_phase0")
PHASE1 = Path("/home/fredcui/foho_phase0/phase1_diagnostics")
OUT = PHASE1 / "selector_v41_comparison_panels_fixed"
OUT.mkdir(parents=True, exist_ok=True)

CASES = ["abox01", "aket01", "alapuse01", "amicuse01", "ascis01"]

def latest_mesh(run_root, patterns):
    run_root = Path(run_root)
    hits = []
    for pat in patterns:
        hits.extend(run_root.glob(pat))
    hits = [p for p in hits if p.exists()]
    return str(sorted(hits)[-1]) if hits else ""

def final_pair(run_root):
    hand = latest_mesh(run_root, [
        "foho_debug/**/final_hand_mesh.ply",
        "guidance_out/*hand*.ply",
        "**/*final*hand*.ply",
    ])
    obj = latest_mesh(run_root, [
        "foho_debug/**/final_obj_mesh.ply",
        "guidance_out/*obj*.ply",
        "**/*final*obj*.ply",
        "**/*object*.ply",
    ])
    return hand, obj

rows = []

for case in CASES:
    input_image = PHASE0 / "inputs/arctic_phase017" / f"{case}.jpg"

    baseline_root = PHASE0 / "runs" / f"arctic_{case}_default"
    old_root = PHASE0 / "runs" / f"arctic_{case}_gpt55_auto_selector_native_v2"
    soft_root = PHASE1 / "arctic5_soft_selected_outputs" / case
    decision_json = soft_root / "selector_v4_1_decision.json"

    b_hand, b_obj = final_pair(baseline_root)
    o_hand, o_obj = final_pair(old_root)

    v_hand = soft_root / "pred_hand_selected.ply"
    v_obj = soft_root / "pred_object_selected.ply"

    decision = {}
    if decision_json.exists():
        decision = json.loads(decision_json.read_text())

    rows.append({
        "case": case,
        "input_image": str(input_image) if input_image.exists() else "",
        "baseline_hand": b_hand,
        "baseline_object": b_obj,
        "old_gpt55_hand": o_hand,
        "old_gpt55_object": o_obj,
        "selector_v41_hand": str(v_hand) if v_hand.exists() else "",
        "selector_v41_object": str(v_obj) if v_obj.exists() else "",
        "selector_v41_decision_json": str(decision_json) if decision_json.exists() else "",
        "selector_v41_chosen_method": decision.get("chosen_method", ""),
        "selector_v41_warning_tags": decision.get("warning_tags", ""),
        "selector_v41_next_stage": decision.get("next_stage", ""),
    })

df = pd.DataFrame(rows)
out_csv = OUT / "selector_v41_panel_manifest_fixed.csv"
df.to_csv(out_csv, index=False)

print("[OK] wrote", out_csv)
print(df.to_string(index=False))

# Hard check.
missing = []
for _, r in df.iterrows():
    for col in [
        "input_image",
        "baseline_hand", "baseline_object",
        "old_gpt55_hand", "old_gpt55_object",
        "selector_v41_hand", "selector_v41_object",
    ]:
        if not str(r[col]):
            missing.append((r["case"], col))

if missing:
    print("[WARN] missing paths:")
    for item in missing:
        print(" ", item)
else:
    print("[OK] all important paths found")
