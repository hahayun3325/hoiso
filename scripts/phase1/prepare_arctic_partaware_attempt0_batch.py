#!/usr/bin/env python
from pathlib import Path
import pandas as pd
import os

ROOT = Path("/home/fredcui/Projects/FollowMyHold")
PROMPT_CSV = ROOT / "docs/phase0/manual_llm_prompts/arctic_phase017_cases_gpt55_partaware_v2.csv"

# Required reruns first. Add "alapuse01" later if you want optional ablation.
CASES = ["abox01", "ascis01", "amicuse01"]

prompt_df = pd.read_csv(PROMPT_CSV)

case_col = "case_id" if "case_id" in prompt_df.columns else "case"
prompt_col = "manual_prompt" if "manual_prompt" in prompt_df.columns else "new_prompt"

for case in CASES:
    row = prompt_df[prompt_df[case_col] == case]
    if row.empty:
        raise RuntimeError(f"Missing prompt for {case} in {PROMPT_CSV}")

    prompt = str(row.iloc[0][prompt_col]).strip()

    old_run_id = f"arctic_{case}_gpt55_auto_selector_native_v2"
    new_run_id = f"arctic_{case}_partaware_v2_attempt0"

    old_env = ROOT / f"configs/generated/pipeline.phase0.{old_run_id}.env"
    new_env = ROOT / f"configs/generated/pipeline.phase1.{new_run_id}.env"

    old_run = Path(f"/home/fredcui/foho_phase0/runs/{old_run_id}")
    new_attempt = Path(f"/home/fredcui/foho_phase0/runs_prompt_refined_v2/arctic_{case}_partaware_v2/attempt0_partaware_prompt")
    new_run = new_attempt / "run_outputs" / new_run_id

    if not old_env.exists():
        raise FileNotFoundError(old_env)

    text = old_env.read_text()
    text = text.replace(str(old_run), str(new_run))
    text = text.replace(old_run_id, new_run_id)
    text = text.replace(
        f"/home/fredcui/foho_phase0/runs/{old_run_id}",
        str(new_run)
    )

    new_env.parent.mkdir(parents=True, exist_ok=True)
    new_env.write_text(text)

    new_run.mkdir(parents=True, exist_ok=True)
    (new_attempt / "logs").mkdir(parents=True, exist_ok=True)
    (new_attempt / "selector_v4_recheck/io_alignment" / f"{case}_partaware_v2_attempt0").mkdir(parents=True, exist_ok=True)

    prompt_path = new_attempt / "object_prompt_partaware_v2.txt"
    prompt_path.write_text(prompt + "\n")

    old_csv = old_run / "manual_gemini_responses.csv"
    new_csv = new_run / "manual_gemini_responses.csv"

    if not old_csv.exists():
        raise FileNotFoundError(old_csv)

    df = pd.read_csv(old_csv)

    candidate_cols = [
        "response",
        "gemini_response",
        "manual_prompt",
        "object_prompt",
        "prompt",
        "object_description",
        "description",
    ]

    hit = None
    for c in candidate_cols:
        if c in df.columns:
            hit = c
            break

    if hit is None:
        raise RuntimeError(f"Cannot find prompt column in {old_csv}; columns={list(df.columns)}")

    df[hit] = prompt
    df.to_csv(new_csv, index=False)

    print("[OK]", case)
    print("  env:", new_env)
    print("  run:", new_run)
    print("  prompt:", prompt_path)
    print("  responses:", new_csv)
