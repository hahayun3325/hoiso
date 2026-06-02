from pathlib import Path
from PIL import Image, ImageDraw
import json

HOME = Path.home()
out_dir = HOME / "foho_phase0/inspection/weekly_report_final"
out_dir.mkdir(parents=True, exist_ok=True)

# Existing assets. The script tolerates missing files and shows placeholders.
assets = [
    {
        "title": "Original input",
        "subtitle": "HO3D/SPAM diagnostic case",
        "path": HOME / "foho_phase0/inputs/test_hoi_clean_002.jpg",
    },
    {
        "title": "Default prompt inpaint",
        "subtitle": "vague prompt → rounded can drift",
        "path": HOME / "foho_phase0/runs/smoke_013/ours_inpaint/test_inpainted_object.png",
    },
    {
        "title": "Default final object",
        "subtitle": "baseline final object",
        "path": HOME / "foho_phase0/inspection/prompt_ablation/smoke013_final_obj.png",
    },
    {
        "title": "Structured prompt inpaint",
        "subtitle": "boxy SPAM description",
        "path": HOME / "foho_phase0/runs/smoke_015_prompt_rect/ours_inpaint/test_inpainted_object.png",
    },
    {
        "title": "Structured Hunyuan object",
        "subtitle": "good object prior",
        "path": HOME / "foho_phase0/inspection/prompt_ablation/smoke015_hunyuan_hoi.png",
    },
    {
        "title": "Fragmented final object",
        "subtitle": "rectified-flow guidance can break object",
        "path": HOME / "foho_phase0/inspection/prompt_ablation/smoke017_final_obj.png",
    },
    {
        "title": "Selector/fallback scene",
        "subtitle": "post-hoc selected object + hand",
        "path": HOME / "foho_phase0/runs/smoke_022_freeze_obj_pose_and_noise/fallback_out/fallback_scene.png",
    },
]

# Fallback search for missing assets by filename pattern.
fallback_patterns = {
    "Default prompt inpaint": ["**/smoke_013*/ours_inpaint/*inpainted*.png", "**/smoke013*inpaint*.png"],
    "Default final object": ["**/smoke013*final*obj*.png"],
    "Structured Hunyuan object": ["**/smoke015*hunyuan*.png", "**/smoke_015*/hunyuan_hoi_out/*.png"],
    "Fragmented final object": ["**/smoke017*final*obj*.png"],
}

search_roots = [HOME / "foho_phase0/inspection", HOME / "foho_phase0/runs"]

def find_fallback(title):
    for root in search_roots:
        for pat in fallback_patterns.get(title, []):
            hits = sorted(root.glob(pat))
            if hits:
                return hits[0]
    return None

def card(item):
    title = item["title"]
    subtitle = item["subtitle"]
    path = Path(item["path"])

    if not path.exists():
        alt = find_fallback(title)
        if alt:
            path = alt

    canvas = Image.new("RGB", (390, 300), "white")
    d = ImageDraw.Draw(canvas)
    d.text((10, 8), title, fill=(0, 0, 0))
    d.text((10, 28), subtitle[:55], fill=(80, 80, 80))

    if path.exists():
        try:
            im = Image.open(path).convert("RGB")
            im.thumbnail((360, 220))
            canvas.paste(im, ((390 - im.width) // 2, 60))
            d.text((10, 280), path.name[:55], fill=(80, 80, 80))
        except Exception as e:
            d.text((20, 130), f"IMAGE ERROR: {e}", fill=(180, 0, 0))
    else:
        d.text((20, 130), "MISSING", fill=(180, 0, 0))
        d.text((20, 150), str(item["path"])[-55:], fill=(180, 0, 0))

    return canvas

cards = [card(x) for x in assets]

cols = 4
rows = (len(cards) + cols - 1) // cols
sheet = Image.new("RGB", (390 * cols, 300 * rows + 70), "white")
d = ImageDraw.Draw(sheet)
d.text((10, 10), "HO3D/SPAM: prompt template + selector story", fill=(0, 0, 0))
d.text((10, 35), "Prompt template improves object prior; final guidance may fragment object; selector/fallback protects geometry.", fill=(60, 60, 60))

for i, c in enumerate(cards):
    sheet.paste(c, ((i % cols) * 390, 70 + (i // cols) * 300))

out = out_dir / "fig1_spam_prompt_template_selector_story.jpg"
sheet.save(out, quality=95)
print("[OK] wrote", out)
