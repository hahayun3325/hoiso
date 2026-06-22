#!/usr/bin/env python
from pathlib import Path
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

REPORT_OUT = Path("/home/fredcui/foho_phase0/phase1_report_assets")
MANIFEST = REPORT_OUT / "manifests/inpainting_asset_manifest.csv"
OUT = REPORT_OUT / "inpainting/arctic5_inpainting_contact_sheet.jpg"

df = pd.read_csv(MANIFEST)

cases = ["abox01", "aket01", "alapuse01", "amicuse01", "ascis01"]
methods = [
    ("baseline", "Baseline"),
    ("selector_gpt55", "Selector + GPT-5.5"),
    ("selector_v41", "Selector-v4.1"),
]

try:
    font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
    font = ImageFont.truetype("DejaVuSans.ttf", 16)
except Exception:
    font_title = font = None

def load_img(path, size=(320, 240)):
    canvas = Image.new("RGB", size, (245, 245, 245))
    d = ImageDraw.Draw(canvas)

    p = Path(str(path))
    if not p.exists():
        d.text((70, 110), "missing", fill=(180, 0, 0), font=font)
        return canvas

    img = Image.open(p).convert("RGB")
    img.thumbnail((size[0]-10, size[1]-30))
    x = (size[0] - img.width) // 2
    y = 25 + (size[1] - 30 - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas

cell_w, cell_h = 320, 270
W = cell_w * (len(methods) + 1)
H = cell_h * (len(cases) + 1)

sheet = Image.new("RGB", (W, H), (255, 255, 255))
draw = ImageDraw.Draw(sheet)

draw.text((10, 10), "ARCTIC-5 inpainting comparison", fill=(0, 0, 0), font=font_title)

for j, (_, label) in enumerate(methods):
    draw.text((cell_w * (j + 1) + 10, 45), label, fill=(0, 0, 0), font=font)

for i, case in enumerate(cases):
    y = cell_h * (i + 1)
    draw.text((10, y + 20), case, fill=(0, 0, 0), font=font_title)

    for j, (method, label) in enumerate(methods):
        row = df[(df["case"] == case) & (df["method_key"] == method)]
        path = row.iloc[0]["copied_image"] if not row.empty else ""

        img = load_img(path)
        x = cell_w * (j + 1)
        sheet.paste(img, (x, y))

OUT.parent.mkdir(parents=True, exist_ok=True)
sheet.save(OUT)
print("[OK] wrote", OUT)
