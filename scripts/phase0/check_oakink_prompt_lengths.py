import pandas as pd
from pathlib import Path

csv_path = Path("docs/phase0/manual_llm_prompts/oakink000_prompt_candidates.csv")
df = pd.read_csv(csv_path)

print("run_id,llm,word_count,char_count,too_long_guess")
for _, r in df.iterrows():
    text = str(r["response"])
    wc = len(text.split())
    cc = len(text)
    # rough warning; CLIP BPE tokens are not words, but this catches long prompts.
    too_long = wc > 55 or cc > 360
    print(f"{r['run_id']},{r['llm']},{wc},{cc},{too_long}")
