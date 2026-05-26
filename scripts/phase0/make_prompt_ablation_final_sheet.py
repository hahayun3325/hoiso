from pathlib import Path
from PIL import Image, ImageDraw

items = [
    ("original input", Path.home() / "foho_phase0/inspection/input_trace/original_input.jpg"),
    ("baseline inpaint", Path.home() / "foho_phase0/runs/smoke_013_octree192_guidance/ours_inpaint/test_inpainted_object.png"),
    ("baseline final object", Path.home() / "foho_phase0/inspection/prompt_ablation/smoke013_final_obj.png"),
    ("rect prompt inpaint", Path.home() / "foho_phase0/runs/smoke_015_prompt_rect/ours_inpaint/test_inpainted_object.png"),
    ("rect prompt Hunyuan mesh", Path.home() / "foho_phase0/inspection/prompt_ablation/smoke015_hunyuan_hoi.png"),
    ("rect prompt final object", Path.home() / "foho_phase0/inspection/prompt_ablation/smoke016_final_obj.png"),
    ("rect prompt final hand", Path.home() / "foho_phase0/inspection/prompt_ablation/smoke016_final_hand.png"),
]

thumbs = []
for title, path in items:
    if not path.exists():
        print("[MISSING]", path)
        continue

    im = Image.open(path).convert("RGB")
    im.thumbnail((340, 240))

    canvas = Image.new("RGB", (380, 320), "white")
    canvas.paste(im, ((380 - im.width) // 2, 45))

    d = ImageDraw.Draw(canvas)
    d.text((10, 10), title, fill=(0, 0, 0))
    d.text((10, 295), path.name, fill=(0, 0, 0))
    thumbs.append(canvas)

sheet = Image.new("RGB", (380 * len(thumbs), 320), "white")
for i, im in enumerate(thumbs):
    sheet.paste(im, (380 * i, 0))

out = Path.home() / "foho_phase0/inspection/prompt_ablation/prompt_ablation_final_sheet.jpg"
sheet.save(out, quality=95)
print("[OK]", out)
