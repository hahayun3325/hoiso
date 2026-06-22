#!/usr/bin/env python
from pathlib import Path
import pandas as pd

REPORT_OUT = Path("/home/fredcui/foho_phase0/phase1_report_assets")
MANIFEST_OUT = REPORT_OUT / "manifests/report_asset_manifest.csv"

CASES = ["abox01", "aket01", "alapuse01", "amicuse01", "ascis01"]

METHODS = {
    "baseline": {
        "method_label": "baseline",
        "run_root_tpl": "/home/fredcui/foho_phase0/runs/arctic_{case}_default",
    },
    "selector_gpt55": {
        "method_label": "selector+gpt-55",
        "run_root_tpl": "/home/fredcui/foho_phase0/runs/arctic_{case}_gpt55_auto_selector_native_v2",
    },
    "selector_v41": {
        "method_label": "selector-v4.1",
        "run_root_tpl": "/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_{case}_selector_v41_refined_pipeline",
    },
}

def latest_pair(run_root: Path):
    hands = sorted(run_root.glob("foho_debug/**/final_hand_mesh.ply"))
    objs = sorted(run_root.glob("foho_debug/**/final_obj_mesh.ply"))

    if hands and objs:
        return hands[-1], objs[-1]

    hands = sorted(run_root.glob("guidance_out/*hand*.ply"))
    objs = sorted(run_root.glob("guidance_out/*obj*.ply"))

    if hands and objs:
        return hands[-1], objs[-1]

    return None, None

rows = []

for case in CASES:
    for method_key, spec in METHODS.items():
        run_root = Path(spec["run_root_tpl"].format(case=case))
        hand, obj = latest_pair(run_root)

        rows.append({
            "case": case,
            "method_key": method_key,
            "method_label": spec["method_label"],
            "run_root": str(run_root),
            "hand_mesh": str(hand) if hand else "",
            "object_mesh": str(obj) if obj else "",
            "mesh_exists": bool(hand and obj and hand.exists() and obj.exists()),
            "input_image": f"/home/fredcui/foho_phase0/inputs/arctic_phase017/{case}.jpg",
        })

df = pd.DataFrame(rows)
MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(MANIFEST_OUT, index=False)

print("[OK] wrote", MANIFEST_OUT)
print(df[["case", "method_key", "mesh_exists", "hand_mesh", "object_mesh"]].to_string(index=False))

if not df["mesh_exists"].all():
    print("[WARN] Some mesh paths are missing. Inspect the manifest before continuing.")
