from pathlib import Path
from PIL import Image, ImageDraw

items = [
    ("Hunyuan initial object", Path.home() / "foho_phase0/inspection/prompt_ablation/smoke019_debug_renders/hunyuan_hoi_out__test_hoi_mesh_ply.png"),
    ("fragmented final object", Path.home() / "foho_phase0/inspection/prompt_ablation/smoke020/smoke020_exported_obj.png"),
    ("selected object + final hand", Path.home() / "foho_phase0/inspection/object_source_selection/fallback_selected_object_plus_final_hand.png"),
    ("bbox-aligned selected object + final hand", Path.home() / "foho_phase0/inspection/object_source_selection/bbox_aligned_selected_object_plus_final_hand.png"),
]

thumbs = []
for title, path in items:
    if not path.exists():
        print("[MISSING]", path)
        continue

    im = Image.open(path).convert("RGB")
    im.thumbnail((420, 300))

    canvas = Image.new("RGB", (470, 380), "white")
    canvas.paste(im, ((470 - im.width) // 2, 60))

    d = ImageDraw.Draw(canvas)
    d.text((10, 10), title, fill=(0, 0, 0))
    d.text((10, 350), path.name[:70], fill=(0, 0, 0))
    thumbs.append(canvas)

sheet = Image.new("RGB", (470 * len(thumbs), 380), "white")
for i, im in enumerate(thumbs):
    sheet.paste(im, (470 * i, 0))

out = Path.home() / "foho_phase0/inspection/object_source_selection/fallback_result_sheet.jpg"
sheet.save(out, quality=95)
print("[OK]", out)
