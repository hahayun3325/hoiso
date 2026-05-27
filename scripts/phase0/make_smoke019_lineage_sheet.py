from pathlib import Path
from PIL import Image, ImageDraw

base = Path.home() / "foho_phase0/inspection/prompt_ablation/smoke019_debug_renders"

items = [
    ("Hunyuan initial complete", base / "hunyuan_hoi_out__test_hoi_mesh_ply.png"),
    ("Before H2M already fragmented", base / "foho_debug__20260527_154141_exp_objtest_inpainted__debug_obj_before_hunyuan2moge_ply.png"),
    ("After H2M still fragmented", base / "foho_debug__20260527_154141_exp_objtest_inpainted__debug_obj_after_hunyuan2moge_ply.png"),
    ("After RT/scale still fragmented", base / "foho_debug__20260527_154141_exp_objtest_inpainted__debug_obj_after_final_rt_scale_ply.png"),
    ("Final debug object", base / "foho_debug__20260527_154141_exp_objtest_inpainted__final_obj_mesh_ply.png"),
    ("Exported test_obj", base / "guidance_out__test_obj_ply.png"),
]

thumbs = []

for title, path in items:
    if not path.exists():
        print("[MISSING]", path)
        continue

    im = Image.open(path).convert("RGB")
    im.thumbnail((360, 260))

    canvas = Image.new("RGB", (410, 340), "white")
    canvas.paste(im, ((410 - im.width) // 2, 55))

    d = ImageDraw.Draw(canvas)
    d.text((10, 10), title, fill=(0, 0, 0))
    d.text((10, 315), path.name[:60], fill=(0, 0, 0))
    thumbs.append(canvas)

sheet = Image.new("RGB", (410 * len(thumbs), 340), "white")

for i, im in enumerate(thumbs):
    sheet.paste(im, (410 * i, 0))

out = Path.home() / "foho_phase0/inspection/prompt_ablation/smoke019_fragmentation_lineage_sheet.jpg"
sheet.save(out, quality=95)
print("[OK]", out)
