#!/usr/bin/env python
from pathlib import Path
import pandas as pd

PIPE_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline")
RUN_ROOT = PIPE_OUT / "runs"
OUT = PIPE_OUT / "selector_v41_full_pipeline_output_manifest.csv"

cases = ["abox01", "aket01", "ascis01", "alapuse01", "amicuse01"]

def latest_pair(run_dir):
    run_dir = Path(run_dir)

    hands = sorted(run_dir.glob("foho_debug/**/final_hand_mesh.ply"))
    objs = sorted(run_dir.glob("foho_debug/**/final_obj_mesh.ply"))

    if hands and objs:
        return str(hands[-1]), str(objs[-1])

    hands = sorted(run_dir.glob("guidance_out/*hand*.ply"))
    objs = sorted(run_dir.glob("guidance_out/*obj*.ply"))

    if hands and objs:
        return str(hands[-1]), str(objs[-1])

    return "", ""

rows = []

for case in cases:
    run_id = f"arctic_{case}_selector_v41_refined_pipeline"
    run_dir = RUN_ROOT / run_id
    hand, obj = latest_pair(run_dir)

    rows.append({
        "case": case,
        "method": "selector_v41_refined_pipeline",
        "run_id": run_id,
        "run_dir": str(run_dir),
        "hand_mesh": hand,
        "object_mesh": obj,
        "exists": bool(hand and obj and Path(hand).exists() and Path(obj).exists()),
        "input_image": f"/home/fredcui/foho_phase0/inputs/arctic_phase017/{case}.jpg",
    })

df = pd.DataFrame(rows)
df.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(df.to_string(index=False))

if not df["exists"].all():
    raise SystemExit("[BAD] some selector-v4.1 full-pipeline meshes are missing")
