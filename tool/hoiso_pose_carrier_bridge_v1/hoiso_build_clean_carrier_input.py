#!/usr/bin/env python3
"""Build and audit a clean RGBA input for a Hunyuan HOI pose carrier.

The unmodeled lower hand is removed from both object support and the carrier
foreground union. The script does not inpaint; pixels outside the union become
transparent in the RGBA output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def load_rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)


def load_mask(path: Path, size: tuple[int, int]) -> np.ndarray:
    im = Image.open(path).convert("L")
    if im.size != size:
        raise ValueError(f"mask size {im.size} does not match RGB size {size}: {path}")
    return np.asarray(im, dtype=np.uint8) >= 128


def save_mask(path: Path, mask: np.ndarray) -> None:
    Image.fromarray((mask.astype(np.uint8) * 255), mode="L").save(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rgb", type=Path, required=True)
    parser.add_argument("--object-mask", type=Path, required=True)
    parser.add_argument("--upper-hand-mask", type=Path, required=True)
    parser.add_argument("--lower-hand-guard", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rgb = load_rgb(args.rgb)
    h, w = rgb.shape[:2]
    size = (w, h)

    obj_raw = load_mask(args.object_mask, size)
    upper_raw = load_mask(args.upper_hand_mask, size)
    lower_guard = load_mask(args.lower_hand_guard, size)

    # Lower unmodeled hand must not contribute to the object or carrier union.
    obj = obj_raw & ~lower_guard
    upper = upper_raw & ~lower_guard
    union = obj | upper
    overlap = obj & upper

    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = union.astype(np.uint8) * 255

    overlay = rgb.astype(np.float32)
    alpha = 0.55
    colors = {
        "object": np.array([0, 255, 0], dtype=np.float32),
        "upper": np.array([255, 0, 0], dtype=np.float32),
        "guard": np.array([255, 0, 255], dtype=np.float32),
        "overlap": np.array([255, 255, 0], dtype=np.float32),
    }
    for mask, color in ((obj, colors["object"]), (upper, colors["upper"]),
                        (lower_guard, colors["guard"]), (overlap, colors["overlap"])):
        overlay[mask] = (1 - alpha) * overlay[mask] + alpha * color

    Image.fromarray(rgba, mode="RGBA").save(args.out_dir / "clean_hoi_pose_carrier_rgba.png")
    Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8), mode="RGB").save(
        args.out_dir / "clean_hoi_pose_carrier_overlay.png"
    )
    save_mask(args.out_dir / "object_mask_clean.png", obj)
    save_mask(args.out_dir / "upper_hand_mask_clean.png", upper)
    save_mask(args.out_dir / "lower_hand_guard.png", lower_guard)
    save_mask(args.out_dir / "carrier_union_mask.png", union)
    save_mask(args.out_dir / "object_upper_overlap_mask.png", overlap)

    report = {
        "schema": "hoiso_clean_pose_carrier_input_audit_v1",
        "raster_wh": [w, h],
        "object_pixels_raw": int(obj_raw.sum()),
        "upper_hand_pixels_raw": int(upper_raw.sum()),
        "lower_hand_guard_pixels": int(lower_guard.sum()),
        "object_pixels_clean": int(obj.sum()),
        "upper_hand_pixels_clean": int(upper.sum()),
        "object_upper_overlap_pixels": int(overlap.sum()),
        "carrier_union_pixels": int(union.sum()),
        "lower_guard_leak_into_object": int((obj & lower_guard).sum()),
        "lower_guard_leak_into_upper_hand": int((upper & lower_guard).sum()),
        "decision": "review_required",
        "authorizes_hunyuan_generation": False,
        "note": (
            "Human review must confirm that the magenta lower-hand guard covers all "
            "unmodeled lower-hand pixels and does not remove laptop geometry."
        ),
    }
    (args.out_dir / "clean_hoi_pose_carrier_input_audit.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
