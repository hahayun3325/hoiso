from pathlib import Path
import pickle
import numpy as np

root = Path.home() / "foho_phase0/inspection/oakink_000/gt_assets/oakink_image_annotation/frame90"

files = sorted(root.rglob("*.pkl"))
print("num_pkl:", len(files))

def summarize(x, name="root", depth=0, max_depth=3):
    pad = "  " * depth

    if depth > max_depth:
        print(pad + name + ": ...")
        return

    if isinstance(x, dict):
        print(pad + f"{name}: dict keys={list(x.keys())[:40]}")
        for k, v in list(x.items())[:20]:
            summarize(v, str(k), depth + 1, max_depth)
    elif isinstance(x, (list, tuple)):
        print(pad + f"{name}: {type(x).__name__} len={len(x)}")
        for i, v in enumerate(x[:5]):
            summarize(v, f"[{i}]", depth + 1, max_depth)
    else:
        try:
            arr = np.asarray(x)
            if arr.dtype.kind in "fiu" and arr.size > 0:
                print(
                    pad + f"{name}: ndarray-like shape={arr.shape} "
                    f"dtype={arr.dtype} first={arr.reshape(-1)[:8].tolist()}"
                )
                return
        except Exception:
            pass
        print(pad + f"{name}: {type(x).__name__} {repr(x)[:120]}")

for p in files:
    print("\n==============================")
    print(p)
    print("==============================")
    try:
        with open(p, "rb") as f:
            data = pickle.load(f)
        summarize(data)
    except Exception as e:
        print("[ERR]", e)
