from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import re

HOME = Path.home()
ROOT = Path("/home/fredcui/Projects/FollowMyHold")

# If your successful reruns used a different suffix, change it here once.
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

LABEL_W = 250
CELL_W = 280
CELL_H = 220
HEADER_H = 90
ROW_H = 250
MARGIN = 20
N_COLS = 5  # crop / inpaint / before42 / after42 / final

TITLE = "OakInk split000 native LLM comparison with automatic internal selector"
SUBTITLE = "Red frame = selector choice between object before Phase 4.2 and object after Phase 4.2"

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
        for h in hits:
            if h.is_file() and h.stat().st_size > 0:
                return h
    return None

def parse_selector_info(base_run_id):
    log_candidates = [
        HOME / f"foho_phase0/logs/{base_run_id}_{SUFFIX}.log",
        HOME / f"foho_phase0/logs/{base_run_id}_selector_auto_frag_native_render.log",
        HOME / f"foho_phase0/logs/{base_run_id}_selector_auto_frag.log",
    ]
    log_path = first_existing(log_candidates)
    selected = "unknown"
    before_frag = "?"
    after_frag = "?"
    if log_path is None:
        return selected, before_frag, after_frag, None

    text = log_path.read_text(errors="ignore")

    # Try several regex styles to be robust.
    patterns = [
        r"before=([0-9.]+).*after=([0-9.]+).*selected=([A-Za-z0-9_]+)",
        r"before_frag=([0-9.]+).*current_frag=([0-9.]+).*selected=([A-Za-z0-9_]+)",
        r"selected=([A-Za-z0-9_]+)",
    ]

    m = re.search(patterns[0], text)
    if m:
        before_frag, after_frag, selected = m.group(1), m.group(2), m.group(3)
        return selected, before_frag, after_frag, log_path

    m = re.search(patterns[1], text)
    if m:
        before_frag, after_frag, selected = m.group(1), m.group(2), m.group(3)
        return selected, before_frag, after_frag, log_path

    m = re.search(patterns[2], text)
    if m:
        selected = m.group(1)

    return selected, before_frag, after_frag, log_path

def get_assets(base_run_id):
    run_id = f"{base_run_id}_{SUFFIX}"
    run_dir = HOME / "foho_phase0/runs" / run_id
    insp_dir = HOME / "foho_phase0/inspection/oakink_000" / run_id
    debug_dir = insp_dir / "internal_selector_debug"

    crop = first_existing([
        run_dir / "oakink_cropped_hoi_1.png",
        insp_dir / "oakink_cropped_hoi_1.png",
        HOME / "foho_phase0/inspection/oakink_000/oakink_cropped_hoi_1.png",
    ]) or first_glob(run_dir, ["*cropped*hoi*.png", "*crop*.png"])

    inpaint = first_existing([
        run_dir / "oakink_inpainted_object.png",
        insp_dir / "oakink_inpainted_object.png",
    ]) or first_glob(run_dir, ["*inpaint*.png", "*inpainted*.png"])

    before42 = first_existing([
        debug_dir / "foho_selector_before_phase42_native.png",
        debug_dir / "selector_before_phase42_native.png",
    ]) or first_glob(debug_dir, ["*before_phase42*native*.png"])

    after42 = first_existing([
        debug_dir / "foho_selector_phase42_before_joint_native.png",
        debug_dir / "selector_phase42_before_joint_native.png",
    ]) or first_glob(debug_dir, ["*phase42_before_joint*native*.png", "*after_phase42*native*.png"])

    final_scene = first_existing([
        run_dir / "rendered_normal_t5.png",
        run_dir / "guidance_out/rendered_normal_t5.png",
    ]) or first_glob(run_dir, ["*rendered_normal_t5*.png", "*rendered_normal*.png"])

    return {
        "run_id": run_id,
        "run_dir": run_dir,
        "debug_dir": debug_dir,
        "crop": crop,
        "inpaint": inpaint,
        "before42": before42,
        "after42": after42,
        "final": final_scene,
    }

def fit_image(img_path, target_w, target_h):
    canvas = Image.new("RGB", (target_w, target_h), (245, 245, 245))
    if img_path is None or not Path(img_path).exists():
        d = ImageDraw.Draw(canvas)
        d.text((target_w//2 - 30, target_h//2 - 10), "MISSING", fill=(180, 0, 0))
        return canvas

    img = Image.open(img_path).convert("RGB")
    img.thumbnail((target_w - 8, target_h - 8))
    x = (target_w - img.width) // 2
    y = (target_h - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas

def paste_cell(sheet, x, y, label, img_path, highlight=False):
    draw = ImageDraw.Draw(sheet)
    draw.text((x, y), label, fill=(0, 0, 0))
    cell_y = y + 20
    tile = fit_image(img_path, CELL_W, CELL_H)
    sheet.paste(tile, (x, cell_y))

    if highlight:
        draw.rectangle(
            [x - 3, cell_y - 3, x + CELL_W + 3, cell_y + CELL_H + 3],
            outline=(220, 0, 0),
            width=6
        )

def main():
    width = MARGIN + LABEL_W + N_COLS * (CELL_W + MARGIN)
    height = HEADER_H + MARGIN + len(RUNS) * ROW_H + MARGIN
    sheet = Image.new("RGB", (width, height), (235, 235, 235))
    draw = ImageDraw.Draw(sheet)

    draw.text((MARGIN, 15), TITLE, fill=(0, 0, 0))
    draw.text((MARGIN, 40), SUBTITLE, fill=(150, 0, 0))

    x0 = MARGIN + LABEL_W
    for i, h in enumerate(COL_HEADERS):
        draw.text((x0 + i * (CELL_W + MARGIN), 65), h, fill=(0, 0, 0))

    for row_idx, (base_run_id, display_name) in enumerate(RUNS):
        y = HEADER_H + row_idx * ROW_H
        assets = get_assets(base_run_id)
        selected, before_frag, after_frag, log_path = parse_selector_info(base_run_id)

        info_lines = [
            display_name,
            base_run_id,
            f"selected: {selected}",
            f"before frag: {before_frag}",
            f"after frag:  {after_frag}",
        ]
        yy = y
        for line in info_lines:
            draw.text((MARGIN, yy), line, fill=(0, 0, 0))
            yy += 18

        before_hl = selected == "before_phase42"
        after_hl = selected in ("phase42_before_joint", "after_phase42", "phase42_before_joint_true")

        paste_cell(sheet, x0 + 0 * (CELL_W + MARGIN), y, "", assets["crop"], highlight=False)
        paste_cell(sheet, x0 + 1 * (CELL_W + MARGIN), y, "", assets["inpaint"], highlight=False)
        paste_cell(sheet, x0 + 2 * (CELL_W + MARGIN), y, "", assets["before42"], highlight=before_hl)
        paste_cell(sheet, x0 + 3 * (CELL_W + MARGIN), y, "", assets["after42"], highlight=after_hl)
        paste_cell(sheet, x0 + 4 * (CELL_W + MARGIN), y, "", assets["final"], highlight=False)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    sheet.save(CANONICAL_OUT)
    print(f"[OK] wrote {OUT}")
    print(f"[OK] updated {CANONICAL_OUT}")

if __name__ == "__main__":
    main()
