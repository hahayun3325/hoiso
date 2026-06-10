from pathlib import Path
from PIL import Image
import numpy as np
import csv
import re

HOME = Path.home()

inputs = {
    "abox01": HOME / "foho_phase0/inputs/arctic_phase017/abox01.jpg",
    "aket01": HOME / "foho_phase0/inputs/arctic_phase017/aket01.jpg",
    "ascis01": HOME / "foho_phase0/inputs/arctic_phase017/ascis01.jpg",
    "alapuse01": HOME / "foho_phase0/inputs/arctic_phase017/alapuse01.jpg",
    "amicuse01": HOME / "foho_phase0/inputs/arctic_phase017/amicuse01.jpg",
}

tokens = {
    "abox01": ["box"],
    "aket01": ["ketchup"],
    "ascis01": ["scissors"],
    "alapuse01": ["laptop"],
    "amicuse01": ["microwave"],
}

roots = [
    Path("/home/fredcui/Projects/BIGS-main/data/arctic_data"),
    Path("/home/fredcui/Projects/arctic/data"),
]

def ahash(path, size=16):
    img = Image.open(path).convert("L").resize((size, size))
    arr = np.asarray(img, dtype=np.float32)
    return arr > arr.mean()

def hdist(a, b):
    return int(np.count_nonzero(a != b))

def parse_arctic_path(p):
    s = str(p)
    # expected: cropped_images/s09/microwave_use_02/3/00419.jpg
    m = re.search(r"cropped_images/(s\d+)/([^/]+)/(\d+)/(\d+)\.jpg", s)
    if not m:
        return {}
    return {
        "subject": m.group(1),
        "seq_name": m.group(2),
        "view_id": m.group(3),
        "frame": str(int(m.group(4))),
    }

rows = []

for case, inp in inputs.items():
    if not inp.exists():
        print("[MISS input]", case, inp)
        continue

    target = ahash(inp)
    case_tokens = tokens[case]

    candidates = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.jpg"):
            s = str(p).lower()
            if "cropped_images" not in s:
                continue
            if not any(tok in s for tok in case_tokens):
                continue
            candidates.append(p)

    print(f"\n===== {case} candidates={len(candidates)} =====")

    scored = []
    for i, p in enumerate(candidates):
        try:
            d = hdist(target, ahash(p))
            scored.append((d, p))
        except Exception:
            pass

    scored.sort(key=lambda x: x[0])

    for rank, (d, p) in enumerate(scored[:20]):
        meta = parse_arctic_path(p)
        row = {
            "case": case,
            "rank": rank,
            "hash_dist": d,
            "path": str(p),
            **meta,
        }
        rows.append(row)
        print(row)

out = HOME / "foho_phase0/inspection/arctic_phase017/arctic_input_provenance_hash_matches.csv"
out.parent.mkdir(parents=True, exist_ok=True)

with open(out, "w", newline="") as f:
    fields = sorted(set().union(*[r.keys() for r in rows])) if rows else ["case"]
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print("\n[OK] wrote", out)
