from pathlib import Path
from PIL import Image, ImageDraw
import trimesh

run = Path.home() / "foho_phase0/runs/oakink_000_baseline"
out_dir = Path.home() / "foho_phase0/inspection/oakink_000"
out_dir.mkdir(parents=True, exist_ok=True)

mesh_cases = {
    "initial_hunyuan": run / "hunyuan_hoi_out/test_hoi_mesh.ply",
    "final_obj": run / "guidance_out/test_obj.ply",
    "final_hand": run / "guidance_out/test_hand.ply",
    "fallback_selected_obj": run / "fallback_out/selected_obj.ply",
    "fallback_selected_hand": run / "fallback_out/selected_hand.ply",
}

render_paths = {}

for name, path in mesh_cases.items():
    if not path.exists():
        print("[MISSING]", name, path)
        continue
    mesh = trimesh.load(path, process=False)
    scene = mesh if isinstance(mesh, trimesh.Scene) else mesh.scene()
    out = out_dir / f"{name}.png"
    out.write_bytes(scene.save_image(resolution=(1024, 1024)))
    render_paths[name] = out
    print("[OK]", out)

# Render fallback scene if exists
fallback_scene = run / "fallback_out/fallback_scene.glb"
if fallback_scene.exists():
    scene = trimesh.load(fallback_scene, process=False)
    out = out_dir / "fallback_scene.png"
    out.write_bytes(scene.save_image(resolution=(1400, 1000)))
    render_paths["fallback_scene"] = out
    print("[OK]", out)

items = [
    ("Initial Hunyuan", render_paths.get("initial_hunyuan")),
    ("Final object", render_paths.get("final_obj")),
    ("Final hand", render_paths.get("final_hand")),
    ("Fallback object", render_paths.get("fallback_selected_obj")),
    ("Fallback scene", render_paths.get("fallback_scene")),
]

thumbs = []
for title, path in items:
    if path is None or not path.exists():
        continue
    im = Image.open(path).convert("RGB")
    im.thumbnail((360, 260))
    canvas = Image.new("RGB", (410, 340), "white")
    canvas.paste(im, ((410 - im.width) // 2, 55))
    d = ImageDraw.Draw(canvas)
    d.text((10, 10), title, fill=(0, 0, 0))
    d.text((10, 315), path.name[:60], fill=(0, 0, 0))
    thumbs.append(canvas)

if thumbs:
    sheet = Image.new("RGB", (410 * len(thumbs), 340), "white")
    for i, im in enumerate(thumbs):
        sheet.paste(im, (410 * i, 0))
    sheet_out = out_dir / "oakink_000_baseline_vs_fallback_sheet.jpg"
    sheet.save(sheet_out, quality=95)
    print("[OK]", sheet_out)
