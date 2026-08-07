#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def load_kps(path: Path) -> np.ndarray:
    arr = np.asarray(np.load(path), dtype=float)
    if arr.shape != (21, 2):
        raise ValueError(f"Expected 21x2 keypoints, got {arr.shape}: {path}")
    return arr


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--image", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--radius", type=int, default=4)
    args = p.parse_args()

    base = Image.open(args.image).convert("RGB")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(args.manifest.open(newline="")))
    for row in rows:
        uid = row.get("candidate_uid", "").strip()
        path = row.get("projected_kps_path", "").strip()
        if not uid or not path:
            continue
        img = base.copy()
        draw = ImageDraw.Draw(img)
        kps = load_kps(Path(path))
        for idx, (x, y) in enumerate(kps):
            r = args.radius
            draw.ellipse((x-r, y-r, x+r, y+r), outline="white", width=2)
            draw.text((x+r+1, y-r-1), str(idx), fill="white")
        draw.rectangle((5, 5, 320, 38), fill="black")
        draw.text((12, 12), uid, fill="white")
        out = args.out_dir / f"candidate_{uid}_indexed_overlay.png"
        img.save(out)
        print(f"[PASS] OVERLAY={out}")


if __name__ == "__main__":
    main()
