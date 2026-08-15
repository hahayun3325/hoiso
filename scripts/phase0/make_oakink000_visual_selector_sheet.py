from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import trimesh
import numpy as np
import json

run = Path.home() / "foho_phase0/runs/oakink_000_baseline"
out_dir = Path.home() / "foho_phase0/inspection/oakink_000"
out_dir.mkdir(parents=True, exist_ok=True)

def load_img(path, title, subtitle=""):
    path = Path(path)
    canvas = Image.new("RGB", (360, 300), "white")
    d = ImageDraw.Draw(canvas)
    d.text((10, 8), title, fill=(0, 0, 0))
    if subtitle:
        d.text((10, 28), subtitle[:52], fill=(80, 80, 80))
    if path.exists():
        im = Image.open(path).convert("RGB")
        im.thumbnail((330, 230))
        canvas.paste(im, ((360 - im.width)//2, 58))
    else:
        d.text((20, 130), f"MISSING:\n{path}", fill=(180, 0, 0))
    return canvas

def render_mesh(path, title, subtitle=""):
    path = Path(path)
    img_path = out_dir / (path.stem + "_render.png")
    canvas = Image.new("RGB", (360, 300), "white")
    d = ImageDraw.Draw(canvas)
    d.text((10, 8), title, fill=(0, 0, 0))
    if subtitle:
        d.text((10, 28), subtitle[:52], fill=(80, 80, 80))
    if not path.exists():
        d.text((20, 130), f"MISSING:\n{path}", fill=(180, 0, 0))
        return canvas
    try:
        mesh = trimesh.load(path, process=False)
        scene = mesh if isinstance(mesh, trimesh.Scene) else mesh.scene()
        img_path.write_bytes(scene.save_image(resolution=(900, 700)))
        im = Image.open(img_path).convert("RGB")
        im.thumbnail((330, 230))
        canvas.paste(im, ((360 - im.width)//2, 58))
    except Exception as e:
        d.text((20, 130), f"RENDER ERROR:\n{e}", fill=(180, 0, 0))
    return canvas

def mesh_score(path):
    path = Path(path)
    if not path.exists():
        return "missing"
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0
    frag = (len(comps) - 1) + (1.0 - largest)
    return f"comp={len(comps)}, frag={frag:.3f}"

fallback_report = run / "fallback_out/fallback_report.json"
selected = "unknown"
if fallback_report.exists():
    data = json.loads(fallback_report.read_text())
    selected = data.get("selected", "unknown")

cards = [
    load_img(
        run / "original_imgs/oakink_full_image_1.png",
        "GT/RGB reference",
        "official OakInk input"
    ),
    load_img(
        run / "cropped_hoi_imgs/oakink_cropped_hoi_1.png",
        "HOI crop",
        "pipeline input crop"
    ),
    load_img(
        run / "ours_inpaint/oakink_inpainted_object.png",
        "Inpainted object",
        "Gemini prompt + FLUX inpaint"
    ),
    render_mesh(
        run / "hunyuan_hoi_out/oakink_hoi_mesh.ply",
        "Hunyuan initial",
        mesh_score(run / "hunyuan_hoi_out/oakink_hoi_mesh.ply")
    ),
    render_mesh(
        run / "guidance_out/oakink_obj.ply",
        "Final guided object",
        mesh_score(run / "guidance_out/oakink_obj.ply")
    ),
    render_mesh(
        run / "fallback_out/selected_obj.ply",
        "Selector output",
        f"selected={selected}; {mesh_score(run / 'fallback_out/selected_obj.ply')}"
    ),
]

cols = 3
rows = 2
sheet = Image.new("RGB", (360 * cols, 300 * rows), "white")
for i, card in enumerate(cards):
    sheet.paste(card, ((i % cols) * 360, (i // cols) * 300))

out = out_dir / "oakink_000_visual_selector_sheet.jpg"
sheet.save(out, quality=95)
print("[OK] wrote", out)
