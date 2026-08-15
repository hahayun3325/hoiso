from pathlib import Path
from PIL import Image, ImageDraw

items = [
    ("original input", Path.home() / "foho_phase0/inspection/input_trace/original_input.jpg"),
    ("013 vague inpaint", Path.home() / "foho_phase0/runs/smoke_013_octree192_guidance/ours_inpaint/test_inpainted_object.png"),
    ("013 final object", Path.home() / "foho_phase0/inspection/prompt_ablation/smoke013_final_obj.png"),
    ("015 structured inpaint", Path.home() / "foho_phase0/runs/smoke_015_prompt_rect/ours_inpaint/test_inpainted_object.png"),
    ("015 Hunyuan mesh", Path.home() / "foho_phase0/inspection/prompt_ablation/smoke015_hunyuan_hoi.png"),
    ("016 final object", Path.home() / "foho_phase0/inspection/prompt_ablation/smoke016_final_obj.png"),
    ("016 final hand", Path.home() / "foho_phase0/inspection/prompt_ablation/smoke016_final_hand.png"),
    ("015 mask overlay", Path.home() / "foho_phase0/inspection/prompt_ablation/smoke015_inpaint_objmask_overlay.jpg"),
]

thumbs = []
for title, path in items:
    if not path.exists():
        print("[MISSING]", path)
        continue

    im = Image.open(path).convert("RGB")
    im.thumbnail((360, 260))

    canvas = Image.new("RGB", (400, 340), "white")
    canvas.paste(im, ((400 - im.width) // 2, 50))

    d = ImageDraw.Draw(canvas)
    d.text((10, 10), title, fill=(0, 0, 0))
    d.text((10, 315), path.name, fill=(0, 0, 0))
    thumbs.append(canvas)

sheet = Image.new("RGB", (400 * len(thumbs), 340), "white")
for i, im in enumerate(thumbs):
    sheet.paste(im, (400 * i, 0))

out = Path.home() / "foho_phase0/inspection/prompt_ablation/smoke013_015_016_comparison_sheet.jpg"
sheet.save(out, quality=95)
print("[OK]", out)
