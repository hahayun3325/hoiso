#!/usr/bin/env python3
"""Build a labelled contact sheet from candidate overlay PNGs."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError(f"argument_error: {message}")


def main() -> int:
    parser = SafeArgumentParser()
    parser.add_argument("--audit-summary", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--columns", type=int, default=2)
    parser.add_argument("--max-width", type=int, default=850)
    args = parser.parse_args()

    data = json.loads(args.audit_summary.read_text())
    candidates = data.get("candidates", [])
    items = []
    for c in candidates:
        path_value = c.get("overlay")
        if not path_value:
            continue
        path = Path(path_value)
        if not path.is_file():
            continue
        items.append((c, Image.open(path).convert("RGB")))
    if not items:
        print("[HOLD] NO_OVERLAYS_AVAILABLE")
        return 0

    cols = max(1, args.columns)
    cell_w = min(args.max_width, max(im.width for _, im in items))
    font = ImageFont.load_default()
    header_h = 44
    resized = []
    for c, im in items:
        scale = min(1.0, cell_w / im.width)
        new_size = (max(1, int(im.width * scale)), max(1, int(im.height * scale)))
        resized.append((c, im.resize(new_size)))
    cell_h = max(im.height for _, im in resized) + header_h
    rows = math.ceil(len(resized) / cols)
    canvas = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(canvas)

    for idx, (c, im) in enumerate(resized):
        row, col = divmod(idx, cols)
        x = col * cell_w
        y = row * cell_h
        label = (
            f"{c.get('candidate_id')} | {c.get('route')}\n"
            f"identity={c.get('source_identity_status')} hand={c.get('handedness')}"
        )
        draw.rectangle((x, y, x + cell_w - 1, y + header_h - 1), fill=(245, 245, 245), outline=(0, 0, 0))
        draw.multiline_text((x + 5, y + 4), label, fill=(0, 0, 0), font=font, spacing=2)
        canvas.paste(im, (x + (cell_w - im.width) // 2, y + header_h))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.out)
    print(f"[PASS] CONTACT_SHEET={args.out}")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as error:
        print(f"[HOLD] CONTACT_SHEET_NOT_WRITTEN={type(error).__name__}: {error}")
        code = 0
    raise SystemExit(code)
