from pathlib import Path
import os
import pickle
import numpy as np

root = Path(os.environ["OAKINK_DIR"]).resolve()
base = root / "extracted/oakink_shape_v2/trigger_sprayer/A01023/d846cc7ddf"

cands = [
    base / "hand_param.pkl",
    base / "s01101/hand_param.pkl",
    base / "s01102/hand_param.pkl",
    base / "s01103/hand_param.pkl",
]

for p in cands:
    print("\n=====", p, "=====")
    if not p.exists():
        print("[MISS]")
        continue

    with open(p, "rb") as f:
        data = pickle.load(f)

    for k in ["pose", "shape", "tsl"]:
        v = np.asarray(data[k])
        print(k, "shape=", v.shape)
        print("  first values:", np.array2string(v[:10], precision=5))
        print("  norm:", float(np.linalg.norm(v)))
