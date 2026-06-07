from pathlib import Path
import pandas as pd
import subprocess

csv_path = Path("docs/phase0/manual_llm_prompts/oakink000_prompt_candidates_short.csv")
df = pd.read_csv(csv_path).fillna("")

for _, r in df.iterrows():
    cmd = [
        "python",
        "scripts/phase0/make_manual_prompt_config.py",
        "--base_config", "configs/pipeline.phase0.oakink000.env",
        "--run_id", r["run_id"],
        "--image_id", r["image_id"],
        "--image_path", r["image_path"],
        "--response", r["response"],
        "--dataset_tag", "oakink",
    ]
    print("\n===== preparing", r["run_id"], "=====")
    cmd = [str(x) for x in cmd]
    subprocess.run(cmd, check=True)
