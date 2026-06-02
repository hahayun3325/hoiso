import argparse
import pandas as pd
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--csv", required=True)
args = ap.parse_args()

df = pd.read_csv(args.csv)
print("run_id,llm,word_count,char_count,too_long_guess")

for _, r in df.iterrows():
    text = str(r["response"])
    wc = len(text.split())
    cc = len(text)
    too_long = wc > 55 or cc > 360
    print(f"{r['run_id']},{r['llm']},{wc},{cc},{too_long}")
