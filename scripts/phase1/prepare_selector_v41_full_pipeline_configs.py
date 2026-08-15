#!/usr/bin/env python
from pathlib import Path
import pandas as pd
import json

ROOT = Path("/home/fredcui/Projects/FollowMyHold")
PIPE_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline")
MANIFEST = PIPE_OUT / "selector_v41_full_pipeline_manifest.csv"

df = pd.read_csv(MANIFEST)

for _, r in df.iterrows():
    case = r["case"]
    template = Path(r["template_config"])
    new_run_id = r["new_run_id"]
    new_run_root = Path(r["new_run_root"])
    new_cfg = ROOT / "configs/generated" / f"pipeline.phase1.{new_run_id}.env"

    if not template.exists():
        raise FileNotFoundError(template)

    text = template.read_text()

    # Replace old run id patterns.
    old_run_ids = [
        f"arctic_{case}_partaware_v2_attempt0",
        f"arctic_{case}_gpt55_auto_selector_native_v2",
        f"arctic_{case}_default",
    ]

    for old in old_run_ids:
        text = text.replace(old, new_run_id)

    # Redirect outputs to the integration root.
    text = text.replace(
        f"/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_{case}_partaware_v2/attempt0_partaware_prompt/run_outputs/{new_run_id}",
        str(new_run_root),
    )

    text = text.replace(
        f"/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_{case}_partaware_v2/attempt0_partaware_prompt/run_outputs/arctic_{case}_partaware_v2_attempt0",
        str(new_run_root),
    )

    text = text.replace(
        f"/home/fredcui/foho_phase0/runs/arctic_{case}_gpt55_auto_selector_native_v2",
        str(new_run_root),
    )

    text = text.replace(
        f"/home/fredcui/foho_phase0/runs/arctic_{case}_default",
        str(new_run_root),
    )

    new_run_root.mkdir(parents=True, exist_ok=True)
    new_cfg.parent.mkdir(parents=True, exist_ok=True)
    new_cfg.write_text(text)

    # Save prompt metadata for traceability.
    meta = {
        "case": case,
        "method": "selector_v41_refined_pipeline",
        "new_run_id": new_run_id,
        "new_run_root": str(new_run_root),
        "template_config": str(template),
        "refined_prompt": r["refined_prompt"],
    }
    (new_run_root / "selector_v41_refined_pipeline_metadata.json").write_text(
        json.dumps(meta, indent=2)
    )

    print("[OK]", case)
    print("  cfg:", new_cfg)
    print("  run:", new_run_root)
