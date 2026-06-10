from pathlib import Path
from PIL import Image, ImageChops
import numpy as np
import csv
import re

HOME = Path.home()
ROOT = Path("/home/fredcui/Projects/arctic/data/cropped_images_structured")

CANDIDATES = {
    "abox01": [
        ROOT / "s01/box_grab_01/2/00081.jpg",
        ROOT / "s01/box_grab_01/2/00082.jpg",
    ],
    "aket01": [
        ROOT / "s01/ketchup_grab_01/7/00147.jpg",
    ],
    "ascis01": [
        ROOT / "s01/scissors_grab_01/5/00364.jpg",
        ROOT / "s01/scissors_grab_01/5/00365.jpg",
    ],
    "alapuse01": [
        ROOT / "s01/laptop_use_01/0/00114.jpg",
    ],
    "amicuse01": [
        ROOT / "s01/microwave_use_01/0/00152.jpg",
    ],
}

def load_rgb(path):
    return Image.open(path).convert("RGB")

def image_diff(a, b):
    ia = load_rgb(a)
    ib = load_rgb(b)

    # Resize only if needed, but exact source should have same size.
    if ia.size != ib.size:
        ib = ib.resize(ia.size)

    diff = ImageChops.difference(ia, ib)
    arr = np.asarray(diff, dtype=np.float32)
    return {
        "same_size": ia.size == load_rgb(b).size,
        "mean_abs_diff": float(arr.mean()),
        "max_abs_diff": int(arr.max()),
        "num_nonzero_pixels": int((arr.sum(axis=2) > 0).sum()),
    }

def parse_path(p):
    s = str(p)
    m = re.search(r"cropped_images_structured/(s\d+)/([^/]+)/(\d+)/(\d+)\.jpg", s)
    if not m:
        return {}
    return {
        "subject": m.group(1),
        "seq_name": m.group(2),
        "view_id": int(m.group(3)),
        "frame": int(m.group(4)),
    }

rows = []

for case, candidates in CANDIDATES.items():
    inp = HOME / f"foho_phase0/inputs/arctic_phase017/{case}.jpg"
    if not inp.exists():
        print("[MISS input]", case, inp)
        continue

    print("\n" + "=" * 80)
    print("case:", case)
    print("input:", inp)

    best = None
    for src in candidates:
        row = {
            "case": case,
            "input_path": str(inp),
            "candidate_path": str(src),
            "candidate_exists": src.exists(),
        }
        row.update(parse_path(src))

        if src.exists():
            row.update(image_diff(inp, src))
        else:
            row.update({
                "same_size": False,
                "mean_abs_diff": 999999.0,
                "max_abs_diff": 999999,
                "num_nonzero_pixels": 999999,
            })

        rows.append(row)
        print(row)

        if best is None or row["mean_abs_diff"] < best["mean_abs_diff"]:
            best = row

    print("BEST:", best)

out = HOME / "foho_phase0/inspection/arctic_phase017/arctic_phase017_provenance_pixel_verify.csv"
out.parent.mkdir(parents=True, exist_ok=True)

fields = sorted(set().union(*[r.keys() for r in rows]))
with open(out, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print("\n[OK] wrote", out)
