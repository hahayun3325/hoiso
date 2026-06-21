#!/usr/bin/env python
from pathlib import Path
import pandas as pd
import re

ROOT = Path("/home/fredcui/Projects/FollowMyHold")
PIPE_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline")
MANIFEST = PIPE_OUT / "selector_v41_full_pipeline_manifest.csv"

def read_env_value(cfg_path: Path, key: str):
    text = cfg_path.read_text()
    m = re.search(rf'^{key}="([^"]*)"', text, flags=re.MULTILINE)
    return m.group(1) if m else ""

def first_existing(paths):
    for p in paths:
        p = Path(p)
        if p.exists():
            return p
    return None

df = pd.read_csv(MANIFEST)

prompt_cols = [
    "response",
    "gemini_response",
    "manual_prompt",
    "object_prompt",
    "prompt",
    "object_description",
    "description",
    "object_name",
]

rows = []

for _, r in df.iterrows():
    case = r["case"]
    run_id = r["new_run_id"]
    refined_prompt = str(r["refined_prompt"]).strip()

    cfg = ROOT / "configs/generated" / f"pipeline.phase1.{run_id}.env"
    if not cfg.exists():
        raise FileNotFoundError(cfg)

    dst_csv = read_env_value(cfg, "GEMINI_RESPONSES")
    if not dst_csv:
        dst_csv = str(Path(r["new_run_root"]) / "manual_gemini_responses.csv")
    dst_csv = Path(dst_csv)
    dst_csv.parent.mkdir(parents=True, exist_ok=True)

    src_csv = first_existing([
        f"/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_{case}_partaware_v2/attempt0_partaware_prompt/run_outputs/arctic_{case}_partaware_v2_attempt0/manual_gemini_responses.csv",
        f"/home/fredcui/foho_phase0/runs/arctic_{case}_gpt55_auto_selector_native_v2/manual_gemini_responses.csv",
        f"/home/fredcui/foho_phase0/runs/arctic_{case}_default/manual_gemini_responses.csv",
    ])

    if src_csv is None:
        raise FileNotFoundError(f"No source manual_gemini_responses.csv found for {case}")

    src_df = pd.read_csv(src_csv)

    if len(src_df) == 0:
        raise RuntimeError(f"Source CSV is empty: {src_csv}")

    # Keep the original schema because get_hunyuan_input already knows how to read it.
    # Only replace the text/prompt-like field.
    hit_cols = [c for c in prompt_cols if c in src_df.columns]

    if not hit_cols:
        print(f"[WARN] No known prompt column in {src_csv}; preserving CSV unchanged.")
    else:
        for c in hit_cols:
            src_df[c] = refined_prompt

    src_df.to_csv(dst_csv, index=False)

    check = pd.read_csv(dst_csv)

    rows.append({
        "case": case,
        "run_id": run_id,
        "source_csv": str(src_csv),
        "dst_csv": str(dst_csv),
        "dst_exists": dst_csv.exists(),
        "num_rows": len(check),
        "columns": ",".join(check.columns),
        "updated_prompt_columns": ",".join(hit_cols),
    })

out = pd.DataFrame(rows)
out_path = PIPE_OUT / "selector_v41_gemini_responses_materialization_report.csv"
out.to_csv(out_path, index=False)

print("[OK] wrote", out_path)
print(out.to_string(index=False))
