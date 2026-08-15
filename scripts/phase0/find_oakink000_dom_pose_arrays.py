from pathlib import Path
import pickle
import numpy as np

p = Path.home() / "foho_phase0/inspection/oakink_000/gt_assets/oakink_image_annotation/dom.pkl"

if not p.exists() or p.stat().st_size == 0:
    raise SystemExit(f"[BAD] missing dom.pkl: {p}")

with open(p, "rb") as f:
    data = pickle.load(f)

hits = []

def walk(x, path="root"):
    if isinstance(x, dict):
        for k, v in x.items():
            walk(v, f"{path}/{k}")
    elif isinstance(x, (list, tuple)):
        for i, v in enumerate(x[:200]):
            walk(v, f"{path}[{i}]")
    else:
        try:
            arr = np.asarray(x)
        except Exception:
            return

        if arr.dtype.kind not in "fiu":
            return

        shape = arr.shape
        key = path.lower()
        interesting_shape = shape in [
            (3,), (4,), (3, 3), (3, 4), (4, 4), (48,), (10,), (21, 3), (778, 3)
        ]
        interesting_name = any(tok in key for tok in [
            "cam", "intr", "extr", "k", "mano", "hand", "joint", "pose",
            "obj", "object", "rot", "trans", "tsl", "r", "t"
        ])

        if interesting_shape or interesting_name:
            hits.append((path, shape, arr.reshape(-1)[:12].tolist()))

walk(data)

print("===== candidate pose / camera arrays =====")
for path, shape, vals in hits[:300]:
    print(path, "shape=", shape, "first=", vals)
