from pathlib import Path
import argparse
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--csv", required=True)
ap.add_argument("--suffix", default=", and preserve the image context.")
args = ap.parse_args()

from transformers import CLIPTokenizer
tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-large-patch14")

df = pd.read_csv(args.csv)
print("run_id,llm,raw_tokens,pipeline_tokens,over_77,pipeline_prompt")

for _, r in df.iterrows():
    raw = str(r["response"])
    pipeline = raw + args.suffix

    raw_tokens = len(tokenizer(raw, truncation=False)["input_ids"])
    pipe_tokens = len(tokenizer(pipeline, truncation=False)["input_ids"])

    print(
        f"{r['run_id']},{r['llm']},"
        f"{raw_tokens},{pipe_tokens},{pipe_tokens > 77},"
        f"\"{pipeline}\""
    )
