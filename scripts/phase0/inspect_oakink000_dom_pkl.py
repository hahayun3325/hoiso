from pathlib import Path
import os
import pickle
import json
import numpy as np
import pandas as pd

root = Path(os.environ["OAKINK_DIR"]).resolve()
row = pd.read_csv("test_splits/oakink_test.csv").iloc[0]

source_txt = root / "extracted/oakink_shape_v2/trigger_sprayer/A01023/d846cc7ddf/source.txt"
source_rel = source_txt.read_text().strip()

candidates = [
    root / source_rel,
    root / "extracted" / source_rel,
    root / "image" / source_rel,
    root / "meta" / source_rel,
    root / "OakInk" / source_rel,
]

print("===== split000 row =====")
print(row.to_string())

print("\n===== source.txt =====")
print(source_txt)
print(source_rel)

print("\n===== dom.pkl candidates =====")
dom_path = None
for p in candidates:
    print("[OK]" if p.exists() else "[MISS]", p)
    if p.exists() and dom_path is None:
        dom_path = p

if dom_path is None:
    print("\n===== searching dom.pkl by sequence/timestamp =====")
    seq = "A01023_0001_0002"
    ts = "2021-10-12-17-13-00"
    hits = [p for p in root.rglob("dom.pkl") if seq in str(p) and ts in str(p)]
    for p in hits[:50]:
        print("[HIT]", p)
    dom_path = hits[0] if hits else None

if dom_path is None:
    raise SystemExit("[BAD] dom.pkl not found")

print("\n===== loading dom.pkl =====")
print("dom_path:", dom_path)

with open(dom_path, "rb") as f:
    data = pickle.load(f)

def summarize(x, name="root", depth=0, max_depth=4):
    pad = "  " * depth
    if depth > max_depth:
        print(pad + name + ": ...")
        return

    if isinstance(x, dict):
        print(pad + f"{name}: dict keys={list(x.keys())[:30]}")
        for k, v in list(x.items())[:30]:
            summarize(v, str(k), depth + 1, max_depth)
    elif isinstance(x, (list, tuple)):
        print(pad + f"{name}: {type(x).__name__} len={len(x)}")
        for i, v in enumerate(x[:5]):
            summarize(v, f"[{i}]", depth + 1, max_depth)
    elif isinstance(x, np.ndarray):
        print(pad + f"{name}: ndarray shape={x.shape} dtype={x.dtype} min={np.nanmin(x) if x.size else 'NA'} max={np.nanmax(x) if x.size else 'NA'}")
    else:
        s = repr(x)
        print(pad + f"{name}: {type(x).__name__} {s[:160]}")

summarize(data)

out = Path.home() / "foho_phase0/inspection/oakink_000/oakink000_dom_pkl_summary.txt"
out.parent.mkdir(parents=True, exist_ok=True)

# Save a text report by re-running summary into a file would be more work;
# for now this command output is tee'd by shell.
print("\n[OK] inspected dom.pkl")
