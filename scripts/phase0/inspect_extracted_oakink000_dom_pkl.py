from pathlib import Path
import pickle
import numpy as np

p = Path.home() / "foho_phase0/inspection/oakink_000/gt_assets/oakink_image_annotation/dom.pkl"

if not p.exists() or p.stat().st_size == 0:
    raise SystemExit(f"[BAD] missing or empty {p}")

with open(p, "rb") as f:
    data = pickle.load(f)

def summarize(x, name="root", depth=0, max_depth=5):
    pad = "  " * depth
    if depth > max_depth:
        print(pad + name + ": ...")
        return

    if isinstance(x, dict):
        print(pad + f"{name}: dict keys={list(x.keys())[:50]}")
        for k, v in list(x.items())[:50]:
            summarize(v, str(k), depth + 1, max_depth)
    elif isinstance(x, (list, tuple)):
        print(pad + f"{name}: {type(x).__name__} len={len(x)}")
        for i, v in enumerate(x[:8]):
            summarize(v, f"[{i}]", depth + 1, max_depth)
    elif isinstance(x, np.ndarray):
        if x.size:
            print(pad + f"{name}: ndarray shape={x.shape} dtype={x.dtype} min={np.nanmin(x)} max={np.nanmax(x)}")
        else:
            print(pad + f"{name}: ndarray shape={x.shape} dtype={x.dtype}")
    else:
        print(pad + f"{name}: {type(x).__name__} {repr(x)[:180]}")

summarize(data)

print("\n===== key search =====")
keys = []
def collect_keys(x, prefix=""):
    if isinstance(x, dict):
        for k, v in x.items():
            path = f"{prefix}/{k}"
            keys.append(path)
            collect_keys(v, path)
    elif isinstance(x, (list, tuple)):
        for i, v in enumerate(x[:20]):
            collect_keys(v, f"{prefix}[{i}]")
collect_keys(data)

for k in keys:
    if any(tok in k.lower() for tok in [
        "cam", "intr", "extr", "mano", "hand", "joint", "pose",
        "obj", "object", "rot", "trans", "tsl", "k", "r", "t"
    ]):
        print(k)
