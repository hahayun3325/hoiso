from pathlib import Path
from PIL import Image, ImageDraw

HOME = Path.home()
OUT = HOME / "foho_phase0/inspection/oakink_000/oakink000_official_qual_panel_skeleton.jpg"
CHECK = OUT.with_suffix(".source_check.txt")

items = [
    ("Input image", HOME / "foho_phase0/runs/oakink000_default_short/original_imgs/oakink_full_image_1.png"),
    ("Crop", HOME / "foho_phase0/runs/oakink000_default_short/cropped_hoi_imgs/oakink_cropped_hoi_1.png"),
    ("Baseline final render", HOME / "foho_phase0/runs/oakink000_default_short/foho_debug"),
    ("GPT-5.5+selector final render", HOME / "foho_phase0/runs/oakink000_gpt55_short_selector_auto_frag_v7_truefile/foho_debug"),
]

def latest_render(debug_dir):
    debug_dir = Path(debug_dir)
    hits = sorted(debug_dir.glob("**/rendered_normal_t5.png"))
    if hits:
        return hits[-1]
    hits = sorted(debug_dir.glob("**/rendered_normal_t4.png"))
    return hits[-1] if hits else None

resolved = []
for name, p in items:
    if p.is_dir():
        p = latest_render(p)
    resolved.append((name, p))

W, H = 320 * len(resolved), 260
canvas = Image.new("RGB", (W, H), (235, 235, 235))
draw = ImageDraw.Draw(canvas)

lines = []
for i, (name, p) in enumerate(resolved):
    x = i * 320
    draw.text((x + 10, 10), name, fill=(0, 0, 0))
    lines.append(f"{name}: {p if p else '[MISSING]'}")

    box = Image.new("RGB", (300, 210), (245, 245, 245))
    bd = ImageDraw.Draw(box)

    if p and Path(p).exists():
        im = Image.open(p).convert("RGB")
        im.thumbnail((290, 190))
        box.paste(im, ((300 - im.width)//2, 35 + (170 - im.height)//2))
    else:
        bd.text((110, 100), "MISSING", fill=(180, 0, 0))

    canvas.paste(box, (x + 10, 40))

OUT.parent.mkdir(parents=True, exist_ok=True)
canvas.save(OUT, quality=95)
CHECK.write_text("\n".join(lines))
print("[OK] wrote", OUT)
print("[OK] wrote", CHECK)
