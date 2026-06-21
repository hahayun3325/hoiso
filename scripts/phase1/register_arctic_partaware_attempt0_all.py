#!/usr/bin/env python
from pathlib import Path
import json
import os
import pandas as pd

CASES = ["abox01", "aket01", "ascis01", "alapuse01", "amicuse01"]

OUT_ROOT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance")
OUT_ROOT.mkdir(parents=True, exist_ok=True)

rows = []

for case in CASES:
    run_id = f"arctic_{case}_partaware_v2_attempt0"
    attempt = Path(f"/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_{case}_partaware_v2/attempt0_partaware_prompt")
    run_dir = attempt / "run_outputs" / run_id

    hands = sorted((run_dir / "foho_debug").glob("*/final_hand_mesh.ply"))
    objs = sorted((run_dir / "foho_debug").glob("*/final_obj_mesh.ply"))

    status = "missing_mesh"
    source_hand = ""
    source_object = ""
    registered_hand = ""
    registered_object = ""

    if hands and objs:
        hand = hands[-1].resolve()
        obj = objs[-1].resolve()

        recheck = attempt / "selector_v4_recheck/io_alignment" / f"{case}_partaware_v2_attempt0"
        recheck.mkdir(parents=True, exist_ok=True)

        dst_hand = recheck / "pred_hand_aligned.ply"
        dst_obj = recheck / "pred_object_aligned.ply"

        for p in [dst_hand, dst_obj]:
            if p.exists() or p.is_symlink():
                p.unlink()

        os.symlink(hand, dst_hand)
        os.symlink(obj, dst_obj)

        status = "registered"
        source_hand = str(hand)
        source_object = str(obj)
        registered_hand = str(dst_hand)
        registered_object = str(dst_obj)

        report = {
            "case": case,
            "attempt": 0,
            "registration_status": status,
            "source_hand": source_hand,
            "source_object": source_object,
            "registered_hand": registered_hand,
            "registered_object": registered_object,
        }

        decision_dir = attempt / "selector_v4_recheck/decision"
        decision_dir.mkdir(parents=True, exist_ok=True)
        (decision_dir / "mesh_registration_report.json").write_text(json.dumps(report, indent=2))

    rows.append({
        "case": case,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "status": status,
        "num_hand_meshes": len(hands),
        "num_object_meshes": len(objs),
        "source_hand": source_hand,
        "source_object": source_object,
        "registered_hand": registered_hand,
        "registered_object": registered_object,
    })

df = pd.DataFrame(rows)
out_csv = OUT_ROOT / "arctic5_partaware_attempt0_registration.csv"
df.to_csv(out_csv, index=False)

print("[OK] wrote", out_csv)
print(df.to_string(index=False))
