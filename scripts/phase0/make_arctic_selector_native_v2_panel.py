from pathlib import Path
from PIL import Image, ImageDraw
import re

HOME = Path.home()

RUNS = [
    ("arctic_abox01_gpt55_auto_selector_native_v2", "abox01 / box"),
    ("arctic_aket01_gpt55_auto_selector_native_v2", "aket01 / ketchup"),
    ("arctic_ascis01_gpt55_auto_selector_native_v2", "ascis01 / scissors"),
    ("arctic_alapuse01_gpt55_auto_selector_native_v2", "alapuse01 / laptop"),
    ("arctic_amicuse01_gpt55_auto_selector_native_v2", "amicuse01 / microwave"),
]

OUT = HOME / "foho_phase0/inspection/arctic_phase017/arctic_selector_native_v2_panel.jpg"
CHECK = OUT.with_suffix(".source_check.txt")

CELL_W, CELL_H = 300, 230
LABEL_W = 270
ROW_H = 260
HEADER_H = 90
MARGIN = 18

COLS = [
    "crop",
    "inpaint",
    "before Phase 4.2",
    "after Phase 4.2",
    "final HOI",
]

def first_glob(root, patterns):
    root = Path(root)
    for pat in patterns:
        hits = sorted(root.glob(pat))
        hits = [p for p in hits if p.is_file() and p.stat().st_size > 0]
        if hits:
            return hits[-1]
    return None

def parse_log(run_id):
    log = HOME / "foho_phase0/logs" / f"{run_id}.rerun_exported.log"
    if not log.exists():
        log = HOME / "foho_phase0/logs" / f"{run_id}.log"
    text = log.read_text(errors="ignore") if log.exists() else ""

    m = re.findall(
        r"before_frag=([0-9.]+), current_frag=([0-9.]+).*?selected=([A-Za-z0-9_]+)",
        text,
    )
    if m:
        before, after, selected = m[-1]
        return log, before, after, selected
    return log, "", "", "unknown"

def card(path, title="", subtitle="", selected=False):
    im = Image.new("RGB", (CELL_W, CELL_H), (245, 245, 245))
    d = ImageDraw.Draw(im)
    d.text((8, 8), title[:40], fill=(0, 0, 0))
    if subtitle:
        d.text((8, 28), subtitle[:55], fill=(80, 80, 80))

    if path and Path(path).exists():
        src = Image.open(path).convert("RGB")
        src.thumbnail((CELL_W - 20, CELL_H - 58))
        x = (CELL_W - src.width) // 2
        y = 50 + (CELL_H - 58 - src.height) // 2
        im.paste(src, (x, y))
    else:
        d.text((CELL_W // 2 - 35, CELL_H // 2), "MISSING", fill=(180, 0, 0))

    if selected:
        d.rectangle([2, 2, CELL_W - 3, CELL_H - 3], outline=(220, 0, 0), width=6)
    return im

def main():
    W = LABEL_W + len(COLS) * CELL_W + 2 * MARGIN
    H = HEADER_H + len(RUNS) * ROW_H + 2 * MARGIN
    canvas = Image.new("RGB", (W, H), (235, 235, 235))
    d = ImageDraw.Draw(canvas)

    d.text((MARGIN, 12), "ARCTIC Phase 0.17 / GPT-5.5 / automatic internal selector", fill=(0, 0, 0))
    d.text((MARGIN, 36), "Red frame = selector choice between before/after Phase 4.2.", fill=(160, 0, 0))

    x0 = MARGIN + LABEL_W
    for i, col in enumerate(COLS):
        d.text((x0 + i * CELL_W + 8, HEADER_H - 28), col, fill=(0, 0, 0))

    source_lines = []

    for r, (run_id, label) in enumerate(RUNS):
        run = HOME / "foho_phase0/runs" / run_id
        y = HEADER_H + r * ROW_H
        log, before_frag, after_frag, selected = parse_log(run_id)

        crop = first_glob(run / "cropped_hoi_imgs", ["*.png"])
        inpaint = first_glob(run / "ours_inpaint", ["*inpainted*object*.png", "*inpaint*.png"])
        before = first_glob(run / "foho_debug", ["**/foho_selector_before_phase42_native.png"])
        after = first_glob(run / "foho_debug", ["**/foho_selector_phase42_before_joint_native.png"])
        final = first_glob(run / "foho_debug", ["**/rendered_normal_t5.png", "**/rendered_normal_t4.png"])

        d.text((MARGIN, y + 10), label, fill=(0, 0, 0))
        d.text((MARGIN, y + 30), run_id, fill=(40, 40, 40))
        d.text((MARGIN, y + 52), f"selected={selected}", fill=(140, 0, 0))
        d.text((MARGIN, y + 72), f"before={before_frag}", fill=(40, 40, 40))
        d.text((MARGIN, y + 92), f"after={after_frag}", fill=(40, 40, 40))

        paths = [crop, inpaint, before, after, final]
        subtitles = ["", "", f"frag={before_frag}", f"frag={after_frag}", ""]
        borders = [
            False,
            False,
            selected == "before_phase42",
            selected == "phase42_before_joint",
            False,
        ]

        for c, p in enumerate(paths):
            canvas.paste(card(p, COLS[c], subtitles[c], borders[c]), (x0 + c * CELL_W, y))

        source_lines.append(f"\n===== {run_id} =====")
        source_lines.append(f"log={log}")
        source_lines.append(f"selected={selected}, before={before_frag}, after={after_frag}")
        for name, p in zip(COLS, paths):
            source_lines.append(f"{name}: {p if p else '[MISSING]'}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, quality=95)
    CHECK.write_text("\n".join(source_lines))
    print("[OK] wrote", OUT)
    print("[OK] wrote", CHECK)

if __name__ == "__main__":
    main()
