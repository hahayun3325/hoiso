#!/usr/bin/env python
from pathlib import Path
import json
import pandas as pd

PHASE1 = Path("/home/fredcui/foho_phase0/phase1_diagnostics")
MANIFEST = PHASE1 / "prompt_refined_rerun/prompt_refined_rerun_manifest.csv"
OUT_ROOT = Path("/home/fredcui/foho_phase0/runs_prompt_refined_v2")

df = pd.read_csv(MANIFEST)

rows = []

for _, r in df.iterrows():
    case = str(r["case_id"])
    run_dir = OUT_ROOT / f"arctic_{case}_partaware_v2"
    attempt0 = run_dir / "attempt0_partaware_prompt"
    attempt1 = run_dir / "attempt1_reinpaint_fallback"

    attempt0.mkdir(parents=True, exist_ok=True)
    attempt1.mkdir(parents=True, exist_ok=True)

    prompt = str(r["new_prompt"]).strip()

    for d in [attempt0, attempt1]:
        (d / "object_prompt_partaware_v2.txt").write_text(prompt + "\n")

    meta = {
        "case_id": case,
        "label": r.get("label", ""),
        "image_path": r.get("image_path", ""),
        "source_path": r.get("source_path", ""),
        "failure_reasons": r.get("failure_reasons", ""),
        "previous_selected_sample_id": r.get("previous_selected_sample_id", ""),
        "previous_method": r.get("previous_method", ""),
        "prompt_template_version": r.get("prompt_template_version", "partaware_v2"),
        "rerun_policy": "direct_partaware_prompt_then_one_reinpaint_fallback",
        "new_prompt": prompt,
        "run_dir": str(run_dir),
        "attempt0_dir": str(attempt0),
        "attempt1_dir": str(attempt1),
        "final_state": "prepared_not_run",
    }

    (run_dir / "rerun_metadata.json").write_text(json.dumps(meta, indent=2))
    (attempt0 / "rerun_metadata.json").write_text(json.dumps(meta | {"attempt": 0}, indent=2))
    (attempt1 / "rerun_metadata.json").write_text(json.dumps(meta | {"attempt": 1}, indent=2))

    rows.append(meta)

summary = pd.DataFrame(rows)
summary_path = PHASE1 / "prompt_refined_rerun/prompt_refined_rerun_dirs_summary.csv"
summary_path.parent.mkdir(parents=True, exist_ok=True)
summary.to_csv(summary_path, index=False)

print("[OK] wrote rerun dirs under", OUT_ROOT)
print("[OK] wrote", summary_path)
print(summary[["case_id", "run_dir", "attempt0_dir", "attempt1_dir", "failure_reasons"]].to_string(index=False))
