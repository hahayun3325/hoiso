#!/usr/bin/env python
from pathlib import Path
import pandas as pd

ROOT = Path("/home/fredcui/Projects/FollowMyHold")
PHASE0 = Path("/home/fredcui/foho_phase0")
PIPE_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline")

PROMPT_CSV = ROOT / "docs/phase0/manual_llm_prompts/arctic_phase017_cases_gpt55_partaware_v2.csv"
OUT = PIPE_OUT / "selector_v41_full_pipeline_manifest.csv"

cases = ["abox01", "aket01", "ascis01", "alapuse01", "amicuse01"]

prompts = pd.read_csv(PROMPT_CSV)
case_col = "case_id" if "case_id" in prompts.columns else "case"
prompt_col = "manual_prompt" if "manual_prompt" in prompts.columns else "new_prompt"

rows = []

for case in cases:
    p = prompts[prompts[case_col] == case]
    if p.empty:
        raise RuntimeError(f"Missing refined prompt for {case} in {PROMPT_CSV}")

    refined_prompt = str(p.iloc[0][prompt_col])

    rows.append({
        "case": case,
        "dataset": "arctic",
        "method": "selector_v41_refined_pipeline",
        "input_image": str(PHASE0 / "inputs/arctic_phase017" / f"{case}.jpg"),
        "template_config": str(ROOT / "configs/generated" / f"pipeline.phase1.arctic_{case}_partaware_v2_attempt0.env"),
        "new_run_id": f"arctic_{case}_selector_v41_refined_pipeline",
        "new_run_root": str(PIPE_OUT / "runs" / f"arctic_{case}_selector_v41_refined_pipeline"),
        "refined_prompt": refined_prompt,
    })

df = pd.DataFrame(rows)
PIPE_OUT.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT, index=False)

print("[OK] wrote", OUT)
print(df[["case", "method", "template_config", "new_run_id", "new_run_root"]].to_string(index=False))
