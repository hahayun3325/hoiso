from pathlib import Path
from PIL import Image, ImageDraw
import re

HOME = Path.home()

RUNS = [
    ("arctic_abox01_gpt55_auto", "abox01 / box"),
    ("arctic_aket01_gpt55_auto", "aket01 / ketchup bottle"),
    ("arctic_ascis01_gpt55_auto", "ascis01 / scissors"),
    ("arctic_alapuse01_gpt55_auto", "alapuse01 / laptop use"),
    ("arctic_amicuse01_gpt55_auto", "amicuse01 / microwave use"),
]

OUT = HOME / "foho_phase0/inspection/arctic_phase017/arctic_phase017_gpt55_native_panel.jpg"
CHECK = HOME / "foho_phase0/inspection/arctic_phase017/arctic_phase017_gpt55_native_panel.source_check.txt"

LABEL_W = 260
CELL_W = 300
CELL_H = 230
HEADER_H = 85
ROW_H = 270
MARGIN = 18

COLS = [
    "input",
    "crop",
    "inpaint",
    "before Phase 4.2",
    "after Phase 4.2",
    "final HOI native render",
]

def first_existing(paths):
    for p in paths:
        if p is None:
            continue
        p = Path(p)
        if p.exists() and p.is_file() and p.stat().st_size > 0:
            return p
    return None

def first_glob(base, patterns):
    base = Path(base)
    for pat in patterns:
        hits = sorted(base.glob(pat))
        hits = [h for h in hits if h.is_file() and h.stat().st_size > 0]
        if hits:
            return hits[0]
    return None

def latest_debug_dir(run, case_id):
    hits = sorted((run / "foho_debug").glob(f"*exp_obj{case_id}_inpainted*"))
    return hits[-1] if hits else None

def parse_selector(log_path):
    if not log_path.exists():
        return {"before": "", "after": "", "selected": "unknown"}
    text = log_path.read_text(errors="ignore")
    m = re.findall(
        r"before_frag=([0-9.]+),\s*(?:current_frag|after_frag)=([0-9.]+).*?selected=([A-Za-z0-9_]+)",
        text,
    )
    if not m:
        return {"before": "", "after": "", "selected": "unknown"}
    before, after, selected = m[-1]
    return {"before": before, "after": after, "selected": selected}

def load_card(path, title, subtitle="", size=(CELL_W, CELL_H), border=False):
    w, h = size
    card = Image.new("RGB", (w, h), (245, 245, 245))
    d = ImageDraw.Draw(card)

    d.text((8, 8), title[:42], fill=(0, 0, 0))
    if subtitle:
        d.text((8, 28), subtitle[:60], fill=(80, 80, 80))

    if path is None:
        d.text((w // 2 - 35, h // 2), "MISSING", fill=(180, 0, 0))
    else:
        im = Image.open(path).convert("RGB")
        im.thumbnail((w - 18, h - 55))
        x = (w - im.width) // 2
        y = 50 + (h - 55 - im.height) // 2
        card.paste(im, (x, y))

    if border:
        d.rectangle([2, 2, w - 3, h - 3], outline=(220, 0, 0), width=5)

    return card

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    W = LABEL_W + len(COLS) * CELL_W + 2 * MARGIN
    H = HEADER_H + len(RUNS) * ROW_H + 2 * MARGIN
    canvas = Image.new("RGB", (W, H), (235, 235, 235))
    d = ImageDraw.Draw(canvas)

    d.text((MARGIN, 10), "ARCTIC Phase 0.17 / GPT-5.5 + automatic internal selector", fill=(0, 0, 0))
    d.text((MARGIN, 32), "Red frame = selector choice. Missing t5 falls back to t4 only for visualization.", fill=(160, 0, 0))

    for ci, col in enumerate(COLS):
        x = MARGIN + LABEL_W + ci * CELL_W
        d.text((x + 8, HEADER_H - 25), col, fill=(0, 0, 0))

    source_lines = []

    for ri, (run_id, label) in enumerate(RUNS):
        case_id = run_id.replace("arctic_", "").replace("_gpt55_auto", "")
        run = HOME / "foho_phase0/runs" / run_id
        debug = latest_debug_dir(run, case_id)
        log = HOME / "foho_phase0/logs" / f"{run_id}.log"
        dec = parse_selector(log)

        y = HEADER_H + ri * ROW_H
        d.text((MARGIN, y + 10), label, fill=(0, 0, 0))
        d.text((MARGIN, y + 32), run_id, fill=(40, 40, 40))
        d.text((MARGIN, y + 54), f"selected={dec['selected']}", fill=(140, 0, 0))
        d.text((MARGIN, y + 76), f"before={dec['before']}", fill=(40, 40, 40))
        d.text((MARGIN, y + 96), f"after={dec['after']}", fill=(40, 40, 40))

        input_img = first_existing([
            HOME / "foho_phase0/inputs/arctic_phase017" / f"{case_id}.jpg",
            run / "original_imgs" / f"{case_id}_full_image_0.png",
            run / "original_imgs" / f"{case_id}_full_image_1.png",
        ])

        crop = first_glob(run / "cropped_hoi_imgs", [f"{case_id}_cropped_hoi_*.png"])
        inpaint = first_existing([run / "ours_inpaint" / f"{case_id}_inpainted_object.png"])

        before = None
        after = None
        final = None
        if debug:
            before = first_existing([
                debug / "foho_selector_before_phase42_native.png",
                debug / "rendered_obj_normal_t3_opt0.png",
            ])
            after = first_existing([
                debug / "foho_selector_phase42_before_joint_native.png",
                debug / "rendered_normal_t4.png",
            ])
            final = first_existing([
                debug / "rendered_normal_t5.png",
                debug / "rendered_normal_t4.png",  # fallback for amicuse01
            ])

        selected = dec["selected"]
        before_selected = selected in ["before_phase42", "before"]
        after_selected = selected in ["phase42_before_joint", "after_phase42", "current"]

        paths = [input_img, crop, inpaint, before, after, final]
        titles = [
            "input",
            "crop",
            "inpaint",
            "before Phase 4.2",
            "after Phase 4.2",
            "final native render",
        ]
        subtitles = [
            "",
            "",
            "",
            "fallback=t3 if selector native missing",
            "fallback=t4 if selector native missing",
            "fallback=t4 if t5 missing",
        ]
        borders = [False, False, False, before_selected, after_selected, False]

        source_lines.append(f"\n===== {run_id} =====")
        source_lines.append(f"debug: {debug if debug else '[MISSING]'}")
        source_lines.append(f"selected: {selected}")
        for name, p in zip(titles, paths):
            source_lines.append(f"{name}: {p if p else '[MISSING]'}")

        for ci, (p, title, sub, border) in enumerate(zip(paths, titles, subtitles, borders)):
            x = MARGIN + LABEL_W + ci * CELL_W
            card = load_card(p, title, sub, border=border)
            canvas.paste(card, (x, y))

    canvas.save(OUT)
    CHECK.write_text("\n".join(source_lines))
    print("[OK] wrote", OUT)
    print("[OK] wrote", CHECK)

if __name__ == "__main__":
    main()
