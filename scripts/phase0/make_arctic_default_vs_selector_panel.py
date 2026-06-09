from pathlib import Path
from PIL import Image, ImageDraw

HOME = Path.home()
CASES = [
    ("abox01", "box"),
    ("aket01", "ketchup"),
    ("ascis01", "scissors"),
    ("alapuse01", "laptop"),
    ("amicuse01", "microwave"),
]

OUT = HOME / "foho_phase0/inspection/arctic_phase017/arctic_default_vs_selector_panel.jpg"
CHECK = OUT.with_suffix(".source_check.txt")

def first_existing(paths):
    for p in paths:
        if p and Path(p).exists() and Path(p).stat().st_size > 0:
            return Path(p)
    return None

def latest_render(run):
    run = Path(run)
    hits = sorted((run / "foho_debug").glob("**/rendered_normal_t5.png"))
    if hits:
        return hits[-1]
    hits = sorted((run / "foho_debug").glob("**/rendered_normal_t4.png"))
    if hits:
        return hits[-1]
    return None

def card(path, title, size=(260, 210)):
    img = Image.new("RGB", size, (245,245,245))
    d = ImageDraw.Draw(img)
    d.text((8,8), title, fill=(0,0,0))
    if path:
        src = Image.open(path).convert("RGB")
        src.thumbnail((size[0]-16, size[1]-40))
        img.paste(src, ((size[0]-src.width)//2, 35))
    else:
        d.text((size[0]//2-35, size[1]//2), "MISSING", fill=(180,0,0))
    return img

cols = ["input", "default final", "GPT-5.5+selector final"]
CELL_W, CELL_H = 270, 220
LABEL_W = 180
ROW_H = CELL_H + 20
W = LABEL_W + len(cols) * CELL_W + 20
H = 70 + len(CASES) * ROW_H

canvas = Image.new("RGB", (W,H), (235,235,235))
d = ImageDraw.Draw(canvas)
d.text((10,10), "ARCTIC Phase 0.17 — Default vs GPT-5.5 + selector", fill=(0,0,0))
d.text((10,32), "Qualitative comparison; not GT-based metric yet.", fill=(120,0,0))

for i, c in enumerate(cols):
    d.text((LABEL_W + i*CELL_W + 10, 50), c, fill=(0,0,0))

lines = []

for r, (case, label) in enumerate(CASES):
    y = 70 + r * ROW_H
    d.text((10, y+10), f"{case} / {label}", fill=(0,0,0))

    default = HOME / "foho_phase0/runs" / f"arctic_{case}_default"
    method = HOME / "foho_phase0/runs" / f"arctic_{case}_gpt55_auto_selector_native_v2"

    input_img = first_existing([
        HOME / "foho_phase0/inputs/arctic_phase017" / f"{case}.jpg",
        default / "original_imgs" / f"{case}_full_image_1.png",
    ])
    default_render = latest_render(default)
    method_render = latest_render(method)

    items = [
        (input_img, "input"),
        (default_render, "default final"),
        (method_render, "GPT-5.5+selector final"),
    ]

    for i, (p, title) in enumerate(items):
        canvas.paste(card(p, title, (CELL_W-10, CELL_H)), (LABEL_W + i*CELL_W, y))

    lines.append(f"\n===== {case} =====")
    lines.append(f"input={input_img if input_img else '[MISSING]'}")
    lines.append(f"default_render={default_render if default_render else '[MISSING]'}")
    lines.append(f"method_render={method_render if method_render else '[MISSING]'}")

OUT.parent.mkdir(parents=True, exist_ok=True)
canvas.save(OUT, quality=95)
CHECK.write_text("\n".join(lines))

print("[OK] wrote", OUT)
print("[OK] wrote", CHECK)
