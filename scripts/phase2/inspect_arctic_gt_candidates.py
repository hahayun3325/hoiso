from pathlib import Path
import argparse
import pickle
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--list", required=True)
args = ap.parse_args()

files = [Path(x.strip()) for x in Path(args.list).read_text().splitlines() if x.strip()]

for p in files:
    print("\n===", p, "===")
    try:
        if p.suffix == ".npz":
            data = np.load(p, allow_pickle=True)
            print("NPZ keys:", list(data.keys()))
            for k in data.keys():
                v = data[k]
                shape = getattr(v, "shape", None)
                dtype = getattr(v, "dtype", None)
                print(" ", k, "shape=", shape, "dtype=", dtype)
        elif p.suffix in [".pkl", ".pickle"]:
            with open(p, "rb") as f:
                data = pickle.load(f)
            if isinstance(data, dict):
                print("PKL keys:", list(data.keys())[:80])
                for k, v in list(data.items())[:80]:
                    shape = getattr(v, "shape", None)
                    print(" ", k, type(v), "shape=", shape)
            else:
                print("PKL type:", type(data))
        else:
            print("mesh/json candidate")
    except Exception as e:
        print("[WARN]", type(e).__name__, e)
