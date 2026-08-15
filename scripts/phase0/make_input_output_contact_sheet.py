from pathlib import Path
from PIL import Image, ImageDraw

items = [
    ("original input", Path.home() / "foho_phase0/inspection/input_trace/original_input.jpg"),
    ("pipeline input", Path.home() / "foho_phase0/inspection/input_trace/pipeline_input.jpg"),
    ("inpainted object", Path.home() / "foho_phase0/runs/smoke_013_octree192_guidance/ours_inpaint/test_inpainted_object.png"),
    ("object mesh preview", Path.home() / "foho_phase0/inspection/test_obj.ply.png"),
    ("hand mesh preview", Path.home() / "foho_phase0/inspection/test_hand.ply.png"),
]

thumbs = []
for title, path in items:
    if not path.exists():
        continue
    im = Image.open(path).convert("RGB")
    im.thumbnail((320, 240))
    canvas = Image.new("RGB", (340, 290), "white")
    canvas.paste(im, ((340 - im.width)//2, 35))
    d = ImageDraw.Draw(canvas)
    d.text((10, 10), title, fill=(0, 0, 0))
    d.text((10, 265), path.name, fill=(0, 0, 0))
    thumbs.append(canvas)

sheet = Image.new("RGB", (340 * len(thumbs), 290), "white")
for i, im in enumerate(thumbs):
    sheet.paste(im, (340 * i, 0))

out = Path.home() / "foho_phase0/inspection/smoke_013_input_output_contact_sheet.jpg"
sheet.save(out, quality=95)
print("[OK]", out)
