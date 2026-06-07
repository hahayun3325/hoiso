from pathlib import Path
from PIL import Image, ImageDraw
import re
import csv

HOME = Path.home()
ROOT = Path("/home/fredcui/Projects/FollowMyHold")

RUNS = [
    ("arctic_abox01_gpt55_auto", "abox01 / box"),
    ("arctic_aket01_gpt55_auto", "aket01 / ketchup bottle"),
    ("arctic_ascis01_gpt55_auto", "ascis01 / scissors"),
    ("arctic_alapuse01_gpt55_auto", "alapuse01 / laptop use"),
    ("arctic_amicuse01_gpt55_auto", "amicuse01 / microwave use"),
]

OUT = HOME / "foho_phase0/inspection/arctic_phase017/arctic_phase017_gpt55_native_panel.jpg"

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

def parse_env(path):
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(errors="ignore").splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

def parse_decision(log_path):
    text = log_path.read_text(errors="ignore") if log_path.exists() else ""

    m = re.findall(
        r"before_frag=([0-9.]+),\s*(?:current_frag|after_frag)=([0-9.]+).*?selected=([A-Za-z0-9_]+)",
        text,
    )
    if m:
        before, after, selected = m[-1]
        return before, after, selected

    m2 = re.findall(r"\[FOHO_INTERNAL_SELECTOR\]\s+selected=([A-Za-z0-9_]+); applied before joint step", text)
    if m2:
        return "", "", m2[-1]

    return "", "", ""

def make_cell(path, title="", subtitle="", selected=False):
    img = Image.new("RGB", (CELL_W, CELL_H), "white")
    d = ImageDraw.Draw(img)

    d.text((8, 6), title[:42], fill=(0, 0, 0))
    if subtitle:
        lines = [subtitle[i:i+46] for i in range(0, len(subtitle), 46)]
        y = 24
        for line in lines[:3]:
            d.text((8, y), line, fill=(70, 70, 70))
            y += 14

    box_y = 62
    box_h = CELL_H - box_y - 8

    if path and Path(path).exists():
        im = Image.open(path).convert("RGB")
        im.thumbnail((CELL_W - 16, box_h), Image.LANCZOS)
        x = (CELL_W - im.width) // 2
        y = box_y + (box_h - im.height) // 2
        img.paste(im, (x, y))
    else:
        d.rectangle([8, box_y, CELL_W - 8, CELL_H - 8], fill=(245, 245, 245))
        d.text((CELL_W // 2 - 35, CELL_H // 2), "MISSING", fill=(180, 0, 0))

    if selected:
        d.rectangle([3, 3, CELL_W - 4, CELL_H - 4], outline=(220, 0, 0), width=6)

    return img

def main():
    rows = []

    for run_id, label in RUNS:
        run = HOME / "foho_phase0/runs" / run_id
        cfg = ROOT / f"configs/generated/pipeline.phase0.{run_id}.env"
        env = parse_env(cfg)
        log = HOME / "foho_phase0/logs" / f"{run_id}.log"

        before_frag, after_frag, selected = parse_decision(log)

        input_img = first_existing([env.get("IMAGE_PATH", "")])
        crop = first_glob(run, ["cropped_hoi_imgs/*.png", "**/cropped_hoi_imgs/*.png"])
        inpaint = first_glob(run, ["ours_inpaint/*.png", "**/ours_inpaint/*.png"])

        before = first_glob(run, [
            "foho_debug/**/*before_phase42*native*.png",
            "**/*before_phase42*native*.png",
        ])
        after = first_glob(run, [
            "foho_debug/**/*phase42_before_joint*native*.png",
            "**/*phase42_before_joint*native*.png",
        ])
        final = first_glob(run, [
            "foho_debug/**/rendered_normal_t5.png",
            "foho_debug/**/rendered_normal_t*.png",
            "**/rendered_normal_t5.png",
            "**/rendered_normal_t*.png",
        ])

        rows.append({
            "run_id": run_id,
            "label": label,
            "before_frag": before_frag,
            "after_frag": after_frag,
            "selected": selected,
            "paths": [input_img, crop, inpaint, before, after, final],
        })

    W = LABEL_W + len(COLS) * CELL_W + MARGIN * 2
    H = HEADER_H + len(rows) * ROW_H + MARGIN * 2
    canvas = Image.new("RGB", (W, H), (235, 235, 235))
    d = ImageDraw.Draw(canvas)

    d.text((MARGIN, 12), "ARCTIC Phase 0.17 / GPT-5.5 + automatic internal selector", fill=(0, 0, 0))
    d.text((MARGIN, 34), "Red frame = selector choice if detected from log.", fill=(140, 0, 0))

    x0 = MARGIN + LABEL_W
    for i, c in enumerate(COLS):
        d.text((x0 + i * CELL_W + 8, HEADER_H - 28), c, fill=(0, 0, 0))

    for r, row in enumerate(rows):
        y = HEADER_H + r * ROW_H
        label_x = MARGIN
        d.text((label_x, y + 10), row["label"], fill=(0, 0, 0))
        d.text((label_x, y + 30), row["run_id"], fill=(50, 50, 50))

        decision_text = f"selected={row['selected'] or 'unknown'}"
        if row["before_frag"] or row["after_frag"]:
            decision_text += f"\nbefore={row['before_frag']}\nafter={row['after_frag']}"
        for j, line in enumerate(decision_text.splitlines()):
            d.text((label_x, y + 55 + 16*j), line, fill=(80, 0, 0))

        for c, path in enumerate(row["paths"]):
            selected_col = False
            if c == 3 and row["selected"] == "before_phase42":
                selected_col = True
            if c == 4 and row["selected"] == "phase42_before_joint":
                selected_col = True

            cell = make_cell(path, selected=selected_col)
            canvas.paste(cell, (x0 + c * CELL_W, y))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, quality=95)
    print("[OK] wrote", OUT)

    # Source check
    src_log = OUT.with_suffix(".source_check.txt")
    with src_log.open("w") as f:
        for row in rows:
            f.write(f"\n===== {row['run_id']} =====\n")
            f.write(f"selected={row['selected']}, before={row['before_frag']}, after={row['after_frag']}\n")
            for col, path in zip(COLS, row["paths"]):
                f.write(f"{col}: {path or '[MISSING]'}\n")
    print("[OK] wrote", src_log)

if __name__ == "__main__":
    main()
