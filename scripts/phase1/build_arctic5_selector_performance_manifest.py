#!/usr/bin/env python
from pathlib import Path
import pandas as pd

cases = ["abox01", "aket01", "ascis01", "alapuse01", "amicuse01"]

rows = []

def latest_pair(run_dir: Path):
    debug = run_dir / "foho_debug"
    hands = sorted(debug.glob("*/final_hand_mesh.ply")) if debug.exists() else []
    objs = sorted(debug.glob("*/final_obj_mesh.ply")) if debug.exists() else []
    if hands and objs:
        return hands[-1], objs[-1]
    gh = run_dir / "guidance_out" / f"{run_dir.name.split('_')[1]}_hand.ply"
    go = run_dir / "guidance_out" / f"{run_dir.name.split('_')[1]}_obj.ply"
    if gh.exists() and go.exists():
        return gh, go
    return None, None

def add(case, method, run_id, run_dir):
    run_dir = Path(run_dir)
    hand, obj = latest_pair(run_dir)
    rows.append({
        "case": case,
        "method": method,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "hand_mesh": str(hand) if hand else "",
        "object_mesh": str(obj) if obj else "",
        "exists": bool(hand and obj and hand.exists() and obj.exists()),
        "input_image": f"/home/fredcui/foho_phase0/inputs/arctic_phase017/{case}.jpg",
    })

for case in cases:
    add(
        case,
        "default_baseline",
        f"arctic_{case}_default",
        f"/home/fredcui/foho_phase0/runs/arctic_{case}_default",
    )

    add(
        case,
        "old_gpt55_selector_v1",
        f"arctic_{case}_gpt55_auto_selector_native_v2",
        f"/home/fredcui/foho_phase0/runs/arctic_{case}_gpt55_auto_selector_native_v2",
    )

    add(
        case,
        "partaware_v2_attempt0",
        f"arctic_{case}_partaware_v2_attempt0",
        f"/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_{case}_partaware_v2/attempt0_partaware_prompt/run_outputs/arctic_{case}_partaware_v2_attempt0",
    )

out = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance/arctic5_selector_performance_manifest.csv")
out.parent.mkdir(parents=True, exist_ok=True)
df = pd.DataFrame(rows)
df.to_csv(out, index=False)

print("[OK] wrote", out)
print(df[["case", "method", "exists", "hand_mesh", "object_mesh"]].to_string(index=False))
