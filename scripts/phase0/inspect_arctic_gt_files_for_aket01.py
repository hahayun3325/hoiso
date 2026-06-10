from pathlib import Path
import json
import pickle
import numpy as np

GT = Path("/home/fredcui/Projects/arctic/unpack/arctic_data/data")
CASE = {
    "case": "aket01",
    "subject": "s01",
    "seq_name": "ketchup_grab_01",
    "view_id": "7",
    "frame": 147,
}

def show_tree(title, paths, limit=120):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    for i, p in enumerate(paths):
        if i >= limit:
            print(f"... truncated after {limit}")
            break
        print(p)

def describe_obj(x, indent=0, name="root"):
    pad = " " * indent
    if isinstance(x, dict):
        print(f"{pad}{name}: dict keys={list(x.keys())[:30]}")
        for k in list(x.keys())[:12]:
            describe_obj(x[k], indent + 2, str(k))
    elif isinstance(x, (list, tuple)):
        print(f"{pad}{name}: {type(x).__name__} len={len(x)}")
        for i, v in enumerate(x[:3]):
            describe_obj(v, indent + 2, f"[{i}]")
    elif hasattr(x, "shape"):
        print(f"{pad}{name}: array shape={x.shape} dtype={getattr(x, 'dtype', None)}")
    else:
        print(f"{pad}{name}: {type(x).__name__} value={str(x)[:120]}")

def try_load(path):
    print("\n" + "-" * 80)
    print("LOAD:", path)
    try:
        if path.suffix == ".json":
            obj = json.loads(path.read_text())
        elif path.suffix in [".pkl", ".pickle"]:
            with open(path, "rb") as f:
                obj = pickle.load(f)
        elif path.suffix == ".npz":
            obj = dict(np.load(path, allow_pickle=True))
        elif path.suffix == ".npy":
            obj = np.load(path, allow_pickle=True)
        else:
            print("[SKIP] unsupported suffix")
            return
        describe_obj(obj)
    except Exception as e:
        print("[ERR]", repr(e))

seq = f"{CASE['subject']}/{CASE['seq_name']}"
seq_flat = f"{CASE['subject']}_{CASE['seq_name']}"

all_files = list(GT.rglob("*"))
related = [
    p for p in all_files
    if p.is_file() and (
        CASE["seq_name"] in str(p)
        or CASE["subject"] in str(p) and any(tok in str(p) for tok in ["split", "meta", "raw_seqs"])
        or "ketchup" in str(p).lower()
    )
]

show_tree("related files for aket01/ketchup", related)

# Load likely useful small files first.
candidates = []
for p in related:
    s = str(p)
    if p.suffix.lower() in [".json", ".pkl", ".pickle", ".npz", ".npy"]:
        if any(tok in s for tok in [
            "splits_json", "meta", "raw_seqs", "splits",
            CASE["seq_name"], "ketchup"
        ]):
            candidates.append(p)

for p in candidates[:40]:
    try_load(p)

print("\n[OK] inspected", len(candidates), "candidate annotation files")
