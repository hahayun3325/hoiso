from pathlib import Path
from PIL import Image, ImageDraw
import re

HOME = Path.home()

runs = [
    ("oakink000_gemini31pro_short", "gemini-3.1-pro"),
    ("oakink000_sonnet46thinking_short", "sonnet-4.6-thinking"),
    ("oakink000_gpt55_short", "gpt-5.5"),
    ("oakink000_gpt55thinking_short", "gpt-5.5-thinking"),
]

def find_first(paths):
    for p in paths:
        p = Path(p)
        if p.exists():
            return p
    return None

def parse_decision(base_id):
    log = HOME / "foho_phase0/logs" / f"{base_id}_selector_auto_frag_final.log"
    text = log.read_text(errors="ignore") if log.exists() else ""
    m = re.findall(
        r"before_frag=([0-9.]+), current_frag=([0-9.]+), margin=([0-9.]+), selected=([A-Za-z0-9_]+)",
        text,
    )
    if not m:
        return {"before": "?", "current": "?", "selected": "missing"}
    before, current, margin, selected = m[-1]
    return {"before": before, "current": current, "selected": selected}

def card(title, subtitle, img=None, decision=None):
    W, H = 430, 320
    out = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(out)
    d.text((8, 8), title[:60], fill=(0, 0, 0))
    d.text((8, 30), subtitle[:70], fill=(70, 70, 70))

    if decision:
        y = 90
        d.text((20, y), f"before Phase 4.2 frag: {decision['before']}", fill=(0, 0, 0)); y += 35
        d.text((20, y), f"after Phase 4.2 frag:  {decision['current']}", fill=(0, 0, 0)); y += 35
        d.text((20, y), f"selected: {decision['selected']}", fill=(180, 0, 0))
        d.rectangle((12, y-8, 390, y+28), outline=(220, 0, 0), width=4)
        d.text((20, y+50), "Decision from log, not from mixed-coordinate render.", fill=(90, 90, 90))
        return out

    if img is None or not Path(img).exists():
        d.text((160, 150), "MISSING", fill=(200, 0, 0))
        return out

    im = Image.open(img).convert("RGB")
    im.thumbnail((400, 245))
    out.paste(im, ((W - im.width)//2, 60))
    d.text((8, 300), Path(img).name[:58], fill=(90, 90, 90))
    return out

rows = []
for base_id, llm in runs:
    run_id = f"{base_id}_selector_auto_frag_final"
    base = HOME / "foho_phase0/runs" / base_id
    run = HOME / "foho_phase0/runs" / run_id

    crop = find_first([
        run / "cropped_hoi_imgs/oakink_cropped_hoi_1.png",
        base / "cropped_hoi_imgs/oakink_cropped_hoi_1.png",
    ])

    inpaint = find_first([
        run / "ours_inpaint/oakink_inpainted_object.png",
        base / "ours_inpaint/oakink_inpainted_object.png",
    ])

    # Prefer existing rendered final scene from your generated panels if available.
    final = find_first([
        HOME / "foho_phase0/inspection/oakink_000" / run_id / "candidate_full_panel_renders/final_obj_plus_final_hand.png",
        HOME / "foho_phase0/inspection/oakink_000" / "auto_selector_llm_grid_v2" / f"{run_id}_final_scene.png",
        HOME / "foho_phase0/inspection/oakink_000" / "auto_selector_llm_grid_v3" / f"{run_id}_final_scene.png",
    ])

    decision = parse_decision(base_id)

    rows.append([
        card(f"{llm}: crop", "cropped HOI input", crop),
        card(f"{llm}: inpaint", "LLM prompt + FLUX", inpaint),
        card(f"{llm}: selector decision", "auto fragmentation score", decision=decision),
        card(f"{llm}: final scene", "final hand-object rendering", final),
    ])

cell_w, cell_h = 430, 320
sheet = Image.new("RGB", (4 * cell_w, len(rows) * cell_h + 70), "white")
d = ImageDraw.Draw(sheet)
d.text((10, 10), "OakInk split000 — automatic internal selector LLM comparison, safe report panel", fill=(0, 0, 0))
d.text((10, 35), "Avoids mixed-coordinate before/after mesh rendering; selector choice shown from logs.", fill=(90, 90, 90))

for r, row in enumerate(rows):
    for c, im in enumerate(row):
        sheet.paste(im, (c * cell_w, 70 + r * cell_h))

out_path = HOME / "foho_phase0/inspection/oakink_000/oakink000_auto_selector_llm_grid_v4_safe.jpg"
out_path.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out_path, quality=95)
print("[OK] wrote", out_path)
