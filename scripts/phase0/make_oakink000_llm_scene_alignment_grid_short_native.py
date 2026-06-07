from pathlib import Path
from PIL import Image, ImageDraw
import re

HOME = Path.home()
SUFFIX = "selector_auto_frag_native_render"

RUNS = [
    ("oakink000_default_short", "Default"),
    ("oakink000_gpt54_short", "GPT-5.4"),
    ("oakink000_gpt54thinking_short", "GPT-5.4-thinking"),
    ("oakink000_sonar2_short", "Sonar 2"),
    ("oakink000_gemini31pro_short", "Gemini-3.1-pro"),
    ("oakink000_sonnet46_short", "Sonnet-4.6"),
    ("oakink000_sonnet46thinking_short", "Sonnet-4.6-thinking"),
    ("oakink000_nemotron3super_short", "Nemotron 3 Super"),
    ("oakink000_gpt55_short", "GPT-5.5"),
    ("oakink000_gpt55thinking_short", "GPT-5.5-thinking"),
    ("oakink000_nemotron3ultra_short", "Nemotron 3 Ultra"),
]

OUT = HOME / "foho_phase0/inspection/oakink_000/oakink000_llm_scene_alignment_grid_short_native.png"
CANONICAL_OUT = HOME / "foho_phase0/inspection/oakink_000/oakink000_llm_scene_alignment_grid_short.png"

LABEL_W = 260
CELL_W = 300
CELL_H = 230
HEADER_H = 90
ROW_H = 265
MARGIN = 18

COL_HEADERS = [
    "cropped input",
    "inpaint",
    "object before Phase 4.2",
    "object after Phase 4.2",
    "final HOI mesh",
]


def first_existing(paths):
    for p in paths:
        p = Path(p)
        if p.exists() and p.is_file() and p.stat().st_size > 0:
            return p
    return None


def first_glob(base, patterns):
    base = Path(base)
    if not base.exists():
        return None
    for pat in patterns:
        hits = sorted(base.glob(pat))
        hits = [h for h in hits if h.is_file() and h.stat().st_size > 0]
        if hits:
            return hits[0]
    return None


def latest_glob(base, patterns):
    base = Path(base)
    if not base.exists():
        return None
    hits_all = []
    for pat in patterns:
        hits_all.extend(base.glob(pat))
    hits_all = [h for h in hits_all if h.is_file() and h.stat().st_size > 0]
    if not hits_all:
        return None
    return sorted(hits_all, key=lambda p: p.stat().st_mtime)[-1]


def parse_selector_info(base_run_id):
    log = HOME / "foho_phase0/logs" / f"{base_run_id}_{SUFFIX}.log"
    selected = "unknown"
    before = "?"
    after = "?"

    if not log.exists():
        return selected, before, after

    text = log.read_text(errors="ignore")

    m = re.findall(
        r"before_frag=([0-9.]+), current_frag=([0-9.]+), margin=([0-9.]+), selected=([A-Za-z0-9_]+)",
        text,
    )
    if m:
        before, after, _, selected = m[-1]
        return selected, before, after

    hits = re.findall(r"selected=([A-Za-z0-9_]+)", text)
    if hits:
        selected = hits[-1]

    return selected, before, after


def get_assets(base_run_id):
    run_id = f"{base_run_id}_{SUFFIX}"
    run_dir = HOME / "foho_phase0/runs" / run_id

    crop = first_glob(run_dir, [
        "cropped_hoi_imgs/*cropped*hoi*.png",
        "cropped_hoi_imgs/*.png",
        "cropped_hoi_imgs_wo_bckg/*.png",
        "original_imgs/*.png",
    ])

    inpaint = first_glob(run_dir, [
        "ours_inpaint/*inpainted*object*.png",
        "ours_inpaint/*inpaint*.png",
        "**/*inpainted*object*.png",
    ])

    before42 = latest_glob(run_dir, [
        "foho_debug/**/*before_phase42*native*.png",
    ])

    after42 = latest_glob(run_dir, [
        "foho_debug/**/*phase42_before_joint*native*.png",
    ])

    final = latest_glob(run_dir, [
        "foho_debug/**/rendered_normal_t5.png",
        "foho_debug/**/rendered_normal_t*.png",
    ])

    return {
        "run_id": run_id,
        "run_dir": run_dir,
        "crop": crop,
        "inpaint": inpaint,
        "before42": before42,
        "after42": after42,
        "final": final,
    }


def fit_image(path, w, h):
    canvas = Image.new("RGB", (w, h), (248, 248, 248))
    draw = ImageDraw.Draw(canvas)

    if path is None or not Path(path).exists():
        draw.text((w // 2 - 35, h // 2 - 8), "MISSING", fill=(180, 0, 0))
        return canvas

    img = Image.open(path).convert("RGB")
    img.thumbnail((w - 8, h - 8))
    x = (w - img.width) // 2
    y = (h - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def paste_cell(sheet, x, y, path, highlight=False):
    draw = ImageDraw.Draw(sheet)
    tile = fit_image(path, CELL_W, CELL_H)
    sheet.paste(tile, (x, y))

    if highlight:
        draw.rectangle(
            [x - 4, y - 4, x + CELL_W + 4, y + CELL_H + 4],
            outline=(220, 0, 0),
            width=6,
        )


def main():
    width = MARGIN + LABEL_W + len(COL_HEADERS) * (CELL_W + MARGIN)
    height = HEADER_H + len(RUNS) * ROW_H + MARGIN

    sheet = Image.new("RGB", (width, height), (235, 235, 235))
    draw = ImageDraw.Draw(sheet)

    draw.text((MARGIN, 12), "OakInk split000 native LLM comparison with automatic internal selector", fill=(0, 0, 0))
    draw.text((MARGIN, 38), "Red frame = selector choice between object before Phase 4.2 and object after Phase 4.2", fill=(160, 0, 0))

    x0 = MARGIN + LABEL_W
    for i, header in enumerate(COL_HEADERS):
        draw.text((x0 + i * (CELL_W + MARGIN), 65), header, fill=(0, 0, 0))

    print("===== panel source check =====")

    for row_idx, (base_run_id, label) in enumerate(RUNS):
        y = HEADER_H + row_idx * ROW_H
        assets = get_assets(base_run_id)
        selected, before_frag, after_frag = parse_selector_info(base_run_id)

        before_hl = selected == "before_phase42"
        after_hl = selected in {"phase42_before_joint", "phase42_before_joint_true", "after_phase42"}

        lines = [
            label,
            base_run_id,
            f"selected: {selected}",
            f"before frag: {before_frag}",
            f"after frag: {after_frag}",
        ]

        yy = y
        for line in lines:
            draw.text((MARGIN, yy), line[:36], fill=(0, 0, 0))
            yy += 18

        paths = [
            assets["crop"],
            assets["inpaint"],
            assets["before42"],
            assets["after42"],
            assets["final"],
        ]

        print("")
        print(f"===== {assets['run_id']} =====")
        for name, p in zip(COL_HEADERS, paths):
            print(f"{name}: {p if p else '[MISSING]'}")
        print(f"selected: {selected}, before={before_frag}, after={after_frag}")

        paste_cell(sheet, x0 + 0 * (CELL_W + MARGIN), y, assets["crop"], False)
        paste_cell(sheet, x0 + 1 * (CELL_W + MARGIN), y, assets["inpaint"], False)
        paste_cell(sheet, x0 + 2 * (CELL_W + MARGIN), y, assets["before42"], before_hl)
        paste_cell(sheet, x0 + 3 * (CELL_W + MARGIN), y, assets["after42"], after_hl)
        paste_cell(sheet, x0 + 4 * (CELL_W + MARGIN), y, assets["final"], False)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    sheet.save(CANONICAL_OUT)
    print("")
    print(f"[OK] wrote {OUT}")
    print(f"[OK] updated {CANONICAL_OUT}")


if __name__ == "__main__":
    main()
