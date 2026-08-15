from pathlib import Path
from PIL import Image, ImageDraw

items = [
    ("original input", Path.home() / "foho_phase0/inspection/input_trace/original_input.jpg"),
    ("baseline inpaint", Path.home() / "foho_phase0/runs/smoke_013_octree192_guidance/ours_inpaint/test_inpainted_object.png"),
    ("baseline object mesh", Path.home() / "foho_phase0/inspection/prompt_ablation/baseline_smoke_013.png"),
    ("rect prompt inpaint", Path.home() / "foho_phase0/runs/smoke_015_prompt_rect/ours_inpaint/test_inpainted_object.png"),
    ("rect prompt object mesh", Path.home() / "foho_phase0/inspection/prompt_ablation/prompt_rect_smoke_015.png"),
]

thumbs = []
for title, path in items:
    if not path.exists():
        print("[MISSING]", path)
        continue

    im = Image.open(path).convert("RGB")
    im.thumbnail((320, 240))

    canvas = Image.new("RGB", (360, 300), "white")
    canvas.paste(im, ((360 - im.width) // 2, 40))

    d = ImageDraw.Draw(canvas)
    d.text((10, 10), title, fill=(0, 0, 0))
    d.text((10, 275), path.name, fill=(0, 0, 0))
    thumbs.append(canvas)

sheet = Image.new("RGB", (360 * len(thumbs), 300), "white")
for i, im in enumerate(thumbs):
    sheet.paste(im, (360 * i, 0))

out = Path.home() / "foho_phase0/inspection/prompt_ablation/prompt_ablation_sheet.jpg"
sheet.save(out, quality=95)
print("[OK]", out)
