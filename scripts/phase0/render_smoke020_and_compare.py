from pathlib import Path
from PIL import Image, ImageDraw
import trimesh

out_dir = Path.home() / "foho_phase0/inspection/prompt_ablation/smoke020"
out_dir.mkdir(parents=True, exist_ok=True)

mesh_cases = {
    "smoke019_exported_obj": Path.home() / "foho_phase0/runs/smoke_019_prompt_rect_guidance_transform_debug/guidance_out/test_obj.ply",
    "smoke020_exported_obj": Path.home() / "foho_phase0/runs/smoke_020_prompt_rect_freeze_obj_noise/guidance_out/test_obj.ply",
    "smoke020_hand": Path.home() / "foho_phase0/runs/smoke_020_prompt_rect_freeze_obj_noise/guidance_out/test_hand.ply",
}

rendered = {}

for name, path in mesh_cases.items():
    if not path.exists():
        print("[MISSING]", path)
        continue
    mesh = trimesh.load(path, process=False)
    png = mesh.scene().save_image(resolution=(1024, 1024))
    out = out_dir / f"{name}.png"
    out.write_bytes(png)
    rendered[name] = out
    print("[OK]", out)

items = [
    ("Hunyuan initial", Path.home() / "foho_phase0/inspection/prompt_ablation/smoke019_debug_renders/hunyuan_hoi_out__test_hoi_mesh_ply.png"),
    ("smoke019 final obj", rendered.get("smoke019_exported_obj")),
    ("smoke020 freeze noise obj", rendered.get("smoke020_exported_obj")),
    ("smoke020 hand", rendered.get("smoke020_hand")),
]

thumbs = []
for title, path in items:
    if path is None or not path.exists():
        print("[MISSING]", title, path)
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

sheet_out = out_dir / "smoke019_vs_smoke020_freeze_noise_sheet.jpg"
sheet.save(sheet_out, quality=95)
print("[OK]", sheet_out)
