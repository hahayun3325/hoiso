#!/usr/bin/env python
from pathlib import Path
import pandas as pd

repo = Path("/home/fredcui/Projects/FollowMyHold")
phase1 = Path("/home/fredcui/foho_phase0/phase1_diagnostics")

selected_summary = phase1 / "selector_v4_selected_only_outputs/selector_v4_selected_only_summary.csv"
prompt_csv = repo / "docs/phase0/manual_llm_prompts/arctic_phase017_cases_gpt55_partaware_v2.csv"
out_csv = phase1 / "prompt_refined_rerun/prompt_refined_rerun_manifest.csv"

sel = pd.read_csv(selected_summary)
prompts = pd.read_csv(prompt_csv)

# ARCTIC only for this prompt-refined rerun.
rejected = sel[
    (sel["final_decision"] == "reject_both_or_rerun")
    & (sel["case"].isin(prompts["case_id"].astype(str)))
].copy()

rows = []
for _, r in rejected.iterrows():
    case = r["case"]
    p = prompts[prompts["case_id"].astype(str) == case].iloc[0]

    rows.append({
        "case_id": case,
        "label": p.get("label", ""),
        "image_path": p.get("image_path", ""),
        "source_path": p.get("source_path", ""),
        "failure_reasons": r.get("failure_reasons", ""),
        "previous_selected_sample_id": r.get("sample_id", ""),
        "previous_method": r.get("method", ""),
        "new_prompt": p["manual_prompt"],
        "prompt_template_version": p.get("prompt_template_version", "partaware_v2"),
        "rerun_policy": "rerun_inpainting_object_init_pose_then_selector_v4",
    })

out = pd.DataFrame(rows)
out_csv.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(out_csv, index=False)

print("[OK] wrote", out_csv)
print(out[["case_id", "failure_reasons", "new_prompt"]].to_string(index=False))
