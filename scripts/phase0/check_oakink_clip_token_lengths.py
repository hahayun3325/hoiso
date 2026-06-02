from pathlib import Path
import argparse
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--csv", required=True)
args = ap.parse_args()

df = pd.read_csv(args.csv)

try:
    from transformers import CLIPTokenizer
    tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-large-patch14")
except Exception as e:
    raise SystemExit(f"[ERROR] Could not load CLIP tokenizer: {e}")

print("run_id,llm,words,chars,clip_tokens,over_77")

for _, r in df.iterrows():
    text = str(r["response"])
    ids = tokenizer(text, truncation=False)["input_ids"]
    print(
        f"{r['run_id']},{r['llm']},"
        f"{len(text.split())},{len(text)},"
        f"{len(ids)},{len(ids) > 77}"
    )
