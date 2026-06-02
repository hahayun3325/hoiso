from pathlib import Path
import pandas as pd
import subprocess
import shlex

csv_path = Path("docs/phase0/manual_llm_prompts/oakink000_prompt_candidates.csv")
df = pd.read_csv(csv_path)

for _, r in df.iterrows():
    response = str(r["response"])
    if "TODO" in response:
        print("[SKIP TODO]", r["run_id"])
        continue

    cmd = [
        "python",
        "scripts/phase0/make_manual_prompt_config.py",
        "--base_config", "configs/pipeline.phase0.oakink000.env",
        "--run_id", r["run_id"],
        "--image_id", r["image_id"],
        "--image_path", r["image_path"],
        "--response", response,
        "--dataset_tag", "oakink",
    ]
    print("\n===== preparing", r["run_id"], "=====")
    subprocess.run(cmd, check=True)
