from pathlib import Path
import argparse
import re
import json
import numpy as np
import trimesh
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("--debug_dir", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--max_items", type=int, default=18)
args = ap.parse_args()

debug_dir = Path(args.debug_dir).expanduser()
out_path = Path(args.out).expanduser()
out_path.parent.mkdir(parents=True, exist_ok=True)

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def score_mesh(path):
    mesh = load_mesh(path)
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0.0
    frag = (len(comps) - 1) + (1.0 - largest)
    return len(comps), frag

def render_mesh(path, out_png):
    mesh = load_mesh(path)
    scene = mesh.scene()
    out_png.write_bytes(scene.save_image(resolution=(850, 650)))

def sort_key(p):
    name = p.name
    t = re.search(r"_t(\d+)_opt(\d+)", name)
    stage = 0
    if "raw_hunyuan" in name:
        stage = 0
    elif "moge_space" in name:
        stage = 1
    elif "transformed_before_joint" in name:
        stage = 2
    if t:
        return (int(t.group(1)), int(t.group(2)), stage)
    return (999, 999, stage)

plys = sorted(debug_dir.glob("*.ply"), key=sort_key)

# Prefer opt0 and opt4 from each timestep to keep the panel readable.
preferred = []
for p in plys:
    if "_opt0" in p.name or "_opt4" in p.name:
        preferred.append(p)
plys = preferred[:args.max_items] if preferred else plys[:args.max_items]

cards = []

render_dir = out_path.parent / "renders"
render_dir.mkdir(parents=True, exist_ok=True)

for p in plys:
    png = render_dir / (p.stem + ".png")
    render_mesh(p, png)

    comp, frag = score_mesh(p)

    title = p.name.replace("phase42_obj_", "")
    title = title.replace("_", " ")

    canvas = Image.new("RGB", (360, 290), "white")
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), title[:48], fill=(0,0,0))
    d.text((8, 30), f"comp={comp}, frag={frag:.2f}", fill=(80,80,80))

    im = Image.open(png).convert("RGB")
    im.thumbnail((330, 220))
    canvas.paste(im, ((360-im.width)//2, 58))
    cards.append(canvas)

cols = 3
rows = max(1, (len(cards) + cols - 1) // cols)
sheet = Image.new("RGB", (360*cols, 290*rows + 70), "white")
d = ImageDraw.Draw(sheet)
d.text((10, 10), "Internal selector debug exports", fill=(0,0,0))
d.text((10, 34), "These are object candidates exported before the joint/alignment block.", fill=(80,80,80))

for i, card in enumerate(cards):
    sheet.paste(card, ((i % cols) * 360, 70 + (i // cols) * 290))

sheet.save(out_path, quality=95)
print("[OK] wrote", out_path)
