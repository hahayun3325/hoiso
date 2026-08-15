#!/usr/bin/env python
from pathlib import Path
import pandas as pd
from PIL import Image, ImageOps, ImageDraw, ImageFont

MANIFEST = Path("docs/phase1/step3_prompt_refined_rerun/aket01_attempt0/aket01_comparison_panel_manifest.csv")
OUT = Path("docs/phase1/step3_prompt_refined_rerun/aket01_attempt0/aket01_comparison_panel.png")

df = pd.read_csv(MANIFEST)

images = []
labels = []

target_h = 420
pad = 20
label_h = 60
title_h = 60

for _, row in df.iterrows():
    p = Path(row["image_path"])
    img = Image.open(p).convert("RGB")
    scale = target_h / img.height
    new_w = int(img.width * scale)
    img = img.resize((new_w, target_h))
    images.append(img)
    labels.append(str(row["label"]))

total_w = pad
for img in images:
    total_w += img.width + pad

canvas_h = title_h + target_h + label_h + pad
canvas = Image.new("RGB", (total_w, canvas_h), "white")
draw = ImageDraw.Draw(canvas)

try:
    font_title = ImageFont.truetype("DejaVuSans.ttf", 28)
    font_label = ImageFont.truetype("DejaVuSans.ttf", 18)
except:
    font_title = ImageFont.load_default()
    font_label = ImageFont.load_default()

title = "aket01 comparison: input vs baseline vs selector-v1 vs selector-v4/refined attempt0"
draw.text((pad, 15), title, fill="black", font=font_title)

x = pad
y = title_h
for img, label in zip(images, labels):
    canvas.paste(img, (x, y))
    draw.rectangle([x, y, x + img.width, y + img.height], outline="black", width=2)
    draw.text((x, y + target_h + 10), label, fill="black", font=font_label)
    x += img.width + pad

OUT.parent.mkdir(parents=True, exist_ok=True)
canvas.save(OUT)
print("[OK] wrote", OUT)
