#!/usr/bin/env python
from pathlib import Path
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import textwrap

PANEL_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_v41_panels")
MANIFEST = PANEL_OUT / "arctic5_selector_v41_panel_manifest.csv"
RENDER_DIR = PANEL_OUT / "visual_renders"
OUT_DIR = PANEL_OUT / "case_panels"
OUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(MANIFEST)

try:
    font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
    font = ImageFont.truetype("DejaVuSans.ttf", 18)
    font_small = ImageFont.truetype("DejaVuSans.ttf", 14)
except Exception:
    font_title = font = font_small = None

def load_img(path, size=(420, 320)):
    p = Path(str(path))
    if not p.exists():
        img = Image.new("RGB", size, (245, 245, 245))
        d = ImageDraw.Draw(img)
        d.text((20, 140), "missing image", fill=(0, 0, 0), font=font)
        return img
    img = Image.open(p).convert("RGB")
    img.thumbnail(size)
    canvas = Image.new("RGB", size, (245, 245, 245))
    x = (size[0] - img.width) // 2
    y = (size[1] - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas

for case, sub in df.groupby("case"):
    sub = sub.copy()

    input_path = sub.iloc[0]["input_image"]
    tiles = []

    input_img = load_img(input_path)
    tiles.append(("input", input_img, "cropped input"))

    preferred_order = ["default_baseline", "old_gpt55_selector_v1", "partaware_v2_attempt0"]

    for method in preferred_order:
        row = sub[sub["method"] == method]
        if row.empty:
            continue
        r = row.iloc[0]
        render = RENDER_DIR / f"{case}__{method}.png"
        img = load_img(render)

        selected = bool(r["is_v41_selected"])
        title = method
        if selected:
            title = "★ SELECTED: " + title

        metrics = (
            f"CD {r['object_cd_mm']:.1f} | F10 {r['object_f10']:.3f}\n"
            f"p5 {r['contact_p5_mm']:.1f} | H-in-O {r['hand_inside_object_ratio']:.3f}\n"
            f"{r['selector_v4_gate']}"
        )
        tiles.append((title, img, metrics))

    W, H = 4 * 450, 470
    panel = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(panel)

    draw.text((20, 15), f"{case}: selector-v4.1 comparison", fill=(0, 0, 0), font=font_title)

    for i, (title, img, caption) in enumerate(tiles):
        x = 20 + i * 450
        y = 60
        panel.paste(img, (x, y))

        color = (20, 90, 60) if title.startswith("★") else (0, 0, 0)
        draw.text((x, y + 330), title, fill=color, font=font)

        wrapped = []
        for line in str(caption).splitlines():
            wrapped.extend(textwrap.wrap(line, width=42))
        draw.text((x, y + 360), "\n".join(wrapped[:5]), fill=(60, 60, 60), font=font_small)

    out = OUT_DIR / f"{case}_selector_v41_panel.png"
    panel.save(out)
    print("[OK]", out)
