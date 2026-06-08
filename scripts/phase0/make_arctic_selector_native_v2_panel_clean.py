from pathlib import Path
from PIL import Image, ImageDraw
import re

HOME = Path.home()

CASES = [
    ("abox01", "box", "rerun_exported.log"),
    ("aket01", "ketchup", "clean_v2.log"),
    ("ascis01", "scissors", "clean_v2.log"),
    ("alapuse01", "laptop", "clean_v2.log"),
    ("amicuse01", "microwave / lowmem", "rerun_exported_lowmem.log"),
]

OUT = HOME / "foho_phase0/inspection/arctic_phase017/arctic_selector_native_v2_panel_clean.jpg"
CHECK = OUT.with_suffix(".source_check.txt")

CELL_W, CELL_H = 300, 230
LABEL_W = 280
ROW_H = 260
HEADER_H = 90
MARGIN = 18
COLS = ["crop", "inpaint", "before 4.2", "after 4.2", "final HOI"]

def first_glob(root, patterns):
    for pat in patterns:
        hits = sorted(Path(root).glob(pat))
        hits = [p for p in hits if p.is_file() and p.stat().st_size > 0]
        if hits:
            return hits[-1]
    return None

def parse_log(run_id, log_suffix):
    log = HOME / "foho_phase0/logs" / f"{run_id}.{log_suffix}"
    if not log.exists():
        log = HOME / "foho_phase0/logs" / f"{run_id}.rerun_exported.log"
    text = log.read_text(errors="ignore") if log.exists() else ""
    m = re.findall(r"before_frag=([0-9.]+), current_frag=([0-9.]+).*?selected=([A-Za-z0-9_]+)", text)
    if m:
        b, a, s = m[-1]
        return log, b, a, s
    return log, "", "", "unknown"

def card(path, title, subtitle="", selected=False):
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

    d.text((MARGIN, 12), "ARCTIC Phase 0.17 / selector-native v2 / clean v2 panel", fill=(0, 0, 0))
    d.text((MARGIN, 36), "Red frame = selected object candidate. amicuse01 uses low-memory final mesh.", fill=(150, 0, 0))

    for i, col in enumerate(COLS):
        d.text((MARGIN + LABEL_W + i * CELL_W + 8, HEADER_H - 25), col, fill=(0, 0, 0))

    lines = []

    for r, (case, label, log_suffix) in enumerate(CASES):
        run_id = f"arctic_{case}_gpt55_auto_selector_native_v2"
        run = HOME / "foho_phase0/runs" / run_id
        log, before_frag, after_frag, selected = parse_log(run_id, log_suffix)

        crop = first_glob(run / "cropped_hoi_imgs", [f"{case}_cropped_hoi_*.png"])
        inpaint = first_glob(run / "ours_inpaint", [f"{case}_inpainted_object.png"])
        before = first_glob(run / "foho_debug", ["**/foho_selector_before_phase42_native.png"])
        after = first_glob(run / "foho_debug", ["**/foho_selector_phase42_before_joint_native.png"])
        final = first_glob(run / "foho_debug", ["**/rendered_normal_t5.png", "**/rendered_normal_t4.png"])

        y = HEADER_H + r * ROW_H
        d.text((MARGIN, y + 10), f"{case} / {label}", fill=(0, 0, 0))
        d.text((MARGIN, y + 32), f"selected={selected}", fill=(150, 0, 0))
        d.text((MARGIN, y + 54), f"before={before_frag}", fill=(40, 40, 40))
        d.text((MARGIN, y + 74), f"after={after_frag}", fill=(40, 40, 40))
        d.text((MARGIN, y + 96), log.name, fill=(80, 80, 80))

        paths = [crop, inpaint, before, after, final]
        cards = [
            card(crop, "crop"),
            card(inpaint, "inpaint"),
            card(before, "before 4.2", f"frag={before_frag}", selected == "before_phase42"),
            card(after, "after 4.2", f"frag={after_frag}", selected == "phase42_before_joint"),
            card(final, "final HOI"),
        ]

        for i, cimg in enumerate(cards):
            canvas.paste(cimg, (MARGIN + LABEL_W + i * CELL_W, y))

        lines.append(f"\n===== {case} =====")
        lines.append(f"log={log}")
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
