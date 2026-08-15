from pathlib import Path
import numpy as np

GT = Path("/home/fredcui/Projects/arctic/unpack/arctic_data/data")
TARGETS = [
    "s01/ketchup_grab_01/7/00147",
    "s01/ketchup_grab_01/7/00147.jpg",
    "ketchup_grab_01",
]

def contains_target(x):
    if isinstance(x, str):
        return any(t in x for t in TARGETS)
    if isinstance(x, bytes):
        try:
            return contains_target(x.decode("utf-8"))
        except Exception:
            return False
    if isinstance(x, dict):
        return any(contains_target(k) or contains_target(v) for k, v in x.items())
    if isinstance(x, (list, tuple)):
        return any(contains_target(v) for v in x)
    if isinstance(x, np.ndarray):
        if x.dtype.kind in {"U", "S", "O"}:
            flat = x.reshape(-1)
            return any(contains_target(v) for v in flat[: min(len(flat), 200000)])
    return False

def describe(x, indent=0, name="root"):
    pad = " " * indent
    if isinstance(x, dict):
        print(f"{pad}{name}: dict keys={list(x.keys())[:50]}")
        for k in list(x.keys())[:40]:
            v = x[k]
            if hasattr(v, "shape"):
                print(f"{pad}  {k}: shape={v.shape} dtype={v.dtype}")
            elif isinstance(v, (list, tuple)):
                print(f"{pad}  {k}: {type(v).__name__} len={len(v)}")
            else:
                print(f"{pad}  {k}: {type(v).__name__} {str(v)[:100]}")
    elif hasattr(x, "shape"):
        print(f"{pad}{name}: array shape={x.shape} dtype={x.dtype}")
    else:
        print(f"{pad}{name}: {type(x)}")

print("===== searching splits =====")
for p in sorted((GT / "splits").rglob("*")):
    if not p.is_file():
        continue
    print("\n---", p)
    try:
        if p.suffix == ".npy":
            data = np.load(p, allow_pickle=True)
            if data.shape == ():
                data = data.item()
        elif p.suffix == ".npz":
            data = dict(np.load(p, allow_pickle=True))
        else:
            print("[SKIP]")
            continue
        hit = contains_target(data)
        print("hit:", hit)
        describe(data)
    except Exception as e:
        print("[ERR]", repr(e))
