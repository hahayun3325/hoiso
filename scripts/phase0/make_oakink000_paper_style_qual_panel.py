from pathlib import Path
from PIL import Image, ImageDraw

HOME = Path.home()

GT_OVERLAY = HOME / "foho_phase0/inspection/oakink_000/oakink000_selected_gt_overlay.jpg"
INPUT = HOME / "foho_phase0/inspection/oakink_000/gt_assets/oakink_image_annotation/selected_south_east_frame90/image.png"

RUNS = {
    "Baseline final render": HOME / "foho_phase0/runs/oakink000_default_short/foho_debug",
    "GPT-5.5 + selector final render": HOME / "foho_phase0/runs/oakink000_gpt55_short_selector_auto_frag_v7_truefile/foho_debug",
}

OUT = HOME / "foho_phase0/inspection/oakink_000/oakink000_paper_style_qual_panel.jpg"
CHECK = OUT.with_suffix(".source_check.txt")

def latest_render(debug_dir):
    debug_dir = Path(debug_dir)
    for pat in ["**/rendered_normal_t5.png", "**/rendered_normal_t4.png", "**/rendered_normal_t3.png"]:
        hits = sorted(debug_dir.glob(pat))
        hits = [p for p in hits if p.is_file() and p.stat().st_size > 0]
        if hits:
            return hits[-1]
    return None

items = [
    ("Input", INPUT),
    ("GT overlay\nred/green=hand, blue=object", GT_OVERLAY),
]
for name, debug_dir in RUNS.items():
    items.append((name, latest_render(debug_dir)))

CELL_W, CELL_H = 360, 270
W = CELL_W * len(items)
H = CELL_H
canvas = Image.new("RGB", (W, H), (238, 238, 238))
draw = ImageDraw.Draw(canvas)

lines = []
for i, (name, path) in enumerate(items):
    x = i * CELL_W
    draw.text((x + 10, 10), name, fill=(0, 0, 0))
    lines.append(f"{name}: {path if path else '[MISSING]'}")

    box = Image.new("RGB", (CELL_W - 20, CELL_H - 55), (245, 245, 245))
    bd = ImageDraw.Draw(box)

    if path and Path(path).exists():
        img = Image.open(path).convert("RGB")
        img.thumbnail((CELL_W - 30, CELL_H - 65))
        box.paste(img, ((box.width - img.width)//2, (box.height - img.height)//2))
    else:
        bd.text((120, 100), "MISSING", fill=(180, 0, 0))

    canvas.paste(box, (x + 10, 50))

OUT.parent.mkdir(parents=True, exist_ok=True)
canvas.save(OUT, quality=95)
CHECK.write_text("\n".join(lines))

print("[OK] wrote", OUT)
print("[OK] wrote", CHECK)
