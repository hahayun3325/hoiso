from pathlib import Path
from PIL import Image, ImageDraw
import pandas as pd
import re

csv_path = Path("docs/phase0/manual_llm_prompts/oakink000_prompt_candidates_short.csv")
df = pd.read_csv(csv_path)

run_ids = [
    "oakink000_gemini31pro_short",
    "oakink000_sonnet46thinking_short",
    "oakink000_gpt55_short",
    "oakink000_gpt55thinking_short",
]

def find_first(paths):
    for p in paths:
        if p and Path(p).exists():
            return Path(p)
    return None

def card(title, subtitle, path):
    canvas = Image.new("RGB", (420, 320), "white")
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), title[:55], fill=(0, 0, 0))
    d.text((8, 30), subtitle[:65], fill=(70, 70, 70))

    if path is None or not Path(path).exists():
        d.text((150, 150), "MISSING", fill=(200, 0, 0))
        return canvas

    im = Image.open(path).convert("RGB")
    im.thumbnail((390, 250))
    canvas.paste(im, ((420 - im.width) // 2, 60))
    d.text((8, 300), Path(path).name[:60], fill=(90, 90, 90))
    return canvas

def keyline(log_path):
    if not log_path.exists():
        return "missing log"
    text = log_path.read_text(errors="ignore")
    m = re.search(r"before_frag=([0-9.]+), current_frag=([0-9.]+).*selected=([a-zA-Z0-9_]+)", text)
    if not m:
        return "missing selector line"
    return f"before={m.group(1)}, current={m.group(2)}, selected={m.group(3)}"

rows = []
for run_id in run_ids:
    hit = df[df["run_id"] == run_id]
    llm = hit.iloc[0]["llm"] if len(hit) else run_id

    base_run = Path.home() / "foho_phase0/runs" / run_id
    auto_run = Path.home() / "foho_phase0/runs" / f"{run_id}_selector_auto_frag_final"
    debug = Path.home() / "foho_phase0/inspection/oakink_000" / f"{run_id}_selector_auto_frag_final" / "internal_selector_debug"
    log = Path.home() / "foho_phase0/logs" / f"{run_id}_selector_auto_frag_final.log"

    crop = find_first([
        base_run / "cropped_hoi_imgs/oakink_cropped_hoi_1.png",
        auto_run / "cropped_hoi_imgs/oakink_cropped_hoi_1.png",
    ])
    inpaint = find_first([
        auto_run / "ours_inpaint/oakink_inpainted_object.png",
        base_run / "ours_inpaint/oakink_inpainted_object.png",
    ])
    initial = find_first([
        Path.home() / "foho_phase0/inspection/oakink_000" / run_id / "pipeline_renders/hunyuan_initial.png",
        Path.home() / "foho_phase0/inspection/oakink_000" / run_id / "candidate_full_panel_renders/3._Hunyuan_full_HOI.png",
    ])
    before_after = find_first([
        debug / "internal_selector_debug_panel.jpg",
    ])
    final_obj_scene = find_first([
        Path.home() / "foho_phase0/inspection/oakink_000" / run_id / "candidate_full_panel_renders/final_obj_plus_final_hand.png",
        Path.home() / "foho_phase0/inspection/oakink_000" / f"{run_id}_selector_auto_frag_final" / "candidate_full_panel_renders/final_obj_plus_final_hand.png",
    ])

    rows.append([
        card(f"{llm}: crop", "cropped HOI input", crop),
        card(f"{llm}: inpaint", "LLM prompt + FLUX", inpaint),
        card(f"{llm}: selector debug", keyline(log), before_after),
        card(f"{llm}: final", "final object + hand", final_obj_scene),
    ])

cols = 4
cell_w, cell_h = 420, 320
sheet = Image.new("RGB", (cols * cell_w, len(rows) * cell_h + 60), "white")
d = ImageDraw.Draw(sheet)
d.text((10, 10), "OakInk split000 — LLM prompt comparison with automatic internal selector", fill=(0, 0, 0))
d.text((10, 34), "Columns: crop | inpaint | selector candidates/decision | final scene", fill=(70, 70, 70))

for r, row in enumerate(rows):
    for c, img in enumerate(row):
        sheet.paste(img, (c * cell_w, 60 + r * cell_h))

out = Path.home() / "foho_phase0/inspection/oakink_000/oakink000_auto_selector_llm_grid.jpg"
out.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out, quality=95)
print("[OK] wrote", out)
