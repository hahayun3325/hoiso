#!/usr/bin/env python
from pathlib import Path
import pandas as pd

repo = Path("/home/fredcui/Projects/FollowMyHold")
phase1 = Path("/home/fredcui/foho_phase0/phase1_diagnostics")

manifest = pd.read_csv(repo / "data/phase1/manifests/phase1_samples.csv")

candidate_file = phase1 / "config_audit/phase1_case_config_candidates.txt"
candidates = []
if candidate_file.exists():
    candidates = [Path(x.strip()) for x in candidate_file.read_text().splitlines() if x.strip()]

rows = []

for _, r in manifest.iterrows():
    sid = r["sample_id"]
    case = r["case"]
    method = r["method"]

    matched = [
        str(p) for p in candidates
        if case.lower() in str(p).lower()
        or sid.lower() in str(p).lower()
        or method.lower() in str(p).lower()
    ]

    rows.append({
        "sample_id": sid,
        "case": case,
        "method": method,
        "phase0_run_id": r.get("phase0_run_id", ""),
        "pred_hand_mesh": r.get("pred_hand_mesh", ""),
        "pred_object_mesh": r.get("pred_object_mesh", ""),
        "align_npz": r.get("align_npz", ""),
        "matched_config_candidates": " | ".join(matched[:5]),
        "manual_original_config_path": "",
        "notes": "Fill manual_original_config_path if automatic match is incomplete.",
    })

out = phase1 / "config_audit/selector_v4_case_config_manifest.csv"
pd.DataFrame(rows).to_csv(out, index=False)

print("[OK] wrote", out)
print(pd.DataFrame(rows)[[
    "sample_id", "case", "method", "matched_config_candidates", "manual_original_config_path"
]].to_string(index=False))
