#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def load_points(path: Path) -> np.ndarray:
    points = np.asarray(np.load(path), dtype=np.float64)
    if points.shape != (21, 2):
        raise ValueError(f"Expected 21x2 array in {path}, got {points.shape}")
    if not np.isfinite(points).all():
        raise ValueError(f"Non-finite points in {path}")
    return points


def draw_points(draw: ImageDraw.ImageDraw, points: np.ndarray, fill: tuple[int, int, int], label: str) -> None:
    radius = 4
    font = ImageFont.load_default()
    for index, (x, y) in enumerate(points):
        x_i, y_i = int(round(x)), int(round(y))
        draw.ellipse((x_i-radius, y_i-radius, x_i+radius, y_i+radius), fill=fill, outline=(0, 0, 0))
        draw.text((x_i+5, y_i-6), str(index), fill=fill, font=font, stroke_width=1, stroke_fill=(0, 0, 0))
    draw.text((8, 8 if label == "target" else 24), label, fill=fill, font=font, stroke_width=1, stroke_fill=(0, 0, 0))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-uid", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--require-size", default="512x512")
    args = parser.parse_args()

    image = Image.open(args.image).convert("RGB")
    required_w, required_h = map(int, args.require_size.lower().split("x"))
    if image.size != (required_w, required_h):
        raise ValueError(f"Expected image size {(required_w, required_h)}, got {image.size}")

    target = load_points(args.target)
    candidate = load_points(args.candidate)
    for name, points in (("target", target), ("candidate", candidate)):
        if ((points[:, 0] < 0) | (points[:, 0] >= required_w) | (points[:, 1] < 0) | (points[:, 1] >= required_h)).any():
            raise ValueError(f"{name} contains points outside the declared full raster")

    draw = ImageDraw.Draw(image)
    draw_points(draw, target, (255, 220, 0), "target")
    draw_points(draw, candidate, (0, 255, 255), f"candidate={args.candidate_uid}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.out)
    print(f"[PASS] OUT={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
