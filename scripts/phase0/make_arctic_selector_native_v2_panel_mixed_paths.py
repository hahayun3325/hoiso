from pathlib import Path
from PIL import Image, ImageDraw
import re

HOME = Path.home()

CASES = [
    ("abox01", "box"),
    ("aket01", "ketchup"),
    ("ascis01", "scissors"),
    ("alapuse01", "laptop"),
    ("amicuse01", "microwave"),
]

OUT = HOME / "foho_phase0/inspection/arctic_phase017/arctic_selector_native_v2_panel_mixed_paths.jpg"
CHECK = OUT.with_suffix(".source_check.txt")

CELL_W, CELL_H = 300, 230
LABEL_W = 260
ROW_H = 260
HEADER_H = 90
MARGIN = 18
COLS = ["crop", "inpaint", "before 4.2", "after 4.2", "final HOI"]

def first(paths):
    for p in paths:
        if p and Path(p).exists() and Path(p).is_file() and Path(p).stat().st_size > 0:
            return Path(p)
    return None

def glob_first(root, pattern):
    hits = sorted(Path(root).glob(pattern))
    hits = [h for h in hits if h.is_file() and h.stat().st_size > 0]
    return hits[-1] if hits else None

def parse_log(case):
    run_id = f"arctic_{case}_gpt55_auto_selector_native_v2"

    candidates = [
        HOME / "foho_phase0/logs" / f"{run_id}.rerun_exported_lowmem.log",
        HOME / "foho_phase0/logs" / f"{run_id}.rerun_exported.log",
        HOME / "foho_phase0/logs" / f"{run_id}.log",
    ]

    for log in candidates:
        if not log.exists():
            continue
        text = log.read_text(errors="ignore")
        m = re.findall(r"before_frag=([0-9.]+), current_frag=([0-9.]+).*?selected=([A-Za-z0-9_]+)", text)
        if m:
            b, a, s = m[-1]
            return b, a, s

    return "", "", "unknown"

def make_card(path, title, subtitle="", selected=False):
    img = Image.new("RGB", (CELL_W, CELL_H), (245, 245, 245))
    d = ImageDraw.Draw(img)
    d.text((8, 8), title, fill=(0, 0, 0))
    if subtitle:
        d.text((8, 28), subtitle[:55], fill=(80, 80, 80))

    if path:
        src = Image.open(path).convert("RGB")
        src.thumbnail((CELL_W - 20, CELL_H - 60))
        x = (CELL_W - src.width) // 2
        y = 52 + (CELL_H - 60 - src.height) // 2
        img.paste(src, (x, y))
    else:
        d.text((CELL_W // 2 - 35, CELL_H // 2), "MISSING", fill=(180, 0, 0))

    if selected:
        d.rectangle([2, 2, CELL_W - 3, CELL_H - 3], outline=(220, 0, 0), width=6)

    return img

def main():
    W = LABEL_W + len(COLS) * CELL_W + 2 * MARGIN
    H = HEADER_H + len(CASES) * ROW_H + 2 * MARGIN
    canvas = Image.new("RGB", (W, H), (235, 235, 235))
    d = ImageDraw.Draw(canvas)

    d.text((MARGIN, 12), "ARCTIC selector-native v2 panel — mixed source paths", fill=(0, 0, 0))
    d.text((MARGIN, 36), "Uses base folder for crop/inpaint/native renders if configs saved them there.", fill=(140, 0, 0))

    for i, col in enumerate(COLS):
        d.text((MARGIN + LABEL_W + i * CELL_W + 8, HEADER_H - 25), col, fill=(0, 0, 0))

    lines = []

    for r, (case, label) in enumerate(CASES):
        base = HOME / "foho_phase0/runs" / f"arctic_{case}_gpt55_auto"
        v2 = HOME / "foho_phase0/runs" / f"arctic_{case}_gpt55_auto_selector_native_v2"

        before_frag, after_frag, selected = parse_log(case)

        crop = first([
            glob_first(v2 / "cropped_hoi_imgs", f"{case}_cropped_hoi_*.png"),
            glob_first(base / "cropped_hoi_imgs", f"{case}_cropped_hoi_*.png"),
        ])

        inpaint = first([
            v2 / "ours_inpaint" / f"{case}_inpainted_object.png",
            base / "ours_inpaint" / f"{case}_inpainted_object.png",
        ])

        before = first([
            glob_first(v2 / "foho_debug", "**/foho_selector_before_phase42_native.png"),
            glob_first(base / "foho_debug", "**/foho_selector_before_phase42_native.png"),
        ])

        after = first([
            glob_first(v2 / "foho_debug", "**/foho_selector_phase42_before_joint_native.png"),
            glob_first(base / "foho_debug", "**/foho_selector_phase42_before_joint_native.png"),
        ])

        final = first([
            glob_first(v2 / "foho_debug", "**/rendered_normal_t5.png"),
            glob_first(v2 / "foho_debug", "**/rendered_normal_t4.png"),
            glob_first(base / "foho_debug", "**/rendered_normal_t5.png"),
            glob_first(base / "foho_debug", "**/rendered_normal_t4.png"),
        ])

        paths = [crop, inpaint, before, after, final]

        y = HEADER_H + r * ROW_H
        d.text((MARGIN, y + 10), f"{case} / {label}", fill=(0, 0, 0))
        d.text((MARGIN, y + 32), f"selected={selected}", fill=(150, 0, 0))
        d.text((MARGIN, y + 54), f"before={before_frag}", fill=(40, 40, 40))
        d.text((MARGIN, y + 74), f"after={after_frag}", fill=(40, 40, 40))

        cards = [
            make_card(crop, "crop"),
            make_card(inpaint, "inpaint"),
            make_card(before, "before 4.2", f"frag={before_frag}", selected == "before_phase42"),
            make_card(after, "after 4.2", f"frag={after_frag}", selected == "phase42_before_joint"),
            make_card(final, "final HOI"),
        ]

        for i, card in enumerate(cards):
            canvas.paste(card, (MARGIN + LABEL_W + i * CELL_W, y))

        lines.append(f"\n===== {case} =====")
        lines.append(f"selected={selected}, before={before_frag}, after={after_frag}")
        for name, p in zip(COLS, paths):
            lines.append(f"{name}: {p if p else '[MISSING]'}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, quality=95)
    CHECK.write_text("\n".join(lines))
    print("[OK] wrote", OUT)
    print("[OK] wrote", CHECK)

if __name__ == "__main__":
    main()
