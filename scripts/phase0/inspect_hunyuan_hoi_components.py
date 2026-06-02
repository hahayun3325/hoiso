from pathlib import Path
import argparse
import numpy as np
import trimesh
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("--run_id", required=True)
args = ap.parse_args()

run = Path.home() / f"foho_phase0/runs/{args.run_id}"
mesh_path = run / "hunyuan_hoi_out/oakink_hoi_mesh.ply"
out_dir = Path.home() / f"foho_phase0/inspection/oakink_000/{args.run_id}/hunyuan_components"
out_dir.mkdir(parents=True, exist_ok=True)

mesh = trimesh.load(mesh_path, process=False)
if isinstance(mesh, trimesh.Scene):
    mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

components = mesh.split(only_watertight=False)
components = sorted(components, key=lambda m: len(m.faces), reverse=True)

print("rank,vertices,faces,bounds_min,bounds_max,center,extents,path")

cards = []

for i, comp in enumerate(components[:12]):
    out_ply = out_dir / f"component_rank{i}.ply"
    comp.export(out_ply)

    scene = comp.scene()
    out_png = out_dir / f"component_rank{i}.png"
    out_png.write_bytes(scene.save_image(resolution=(700, 550)))

    print(
        f"{i},{len(comp.vertices)},{len(comp.faces)},"
        f"\"{np.round(comp.bounds[0],5).tolist()}\","
        f"\"{np.round(comp.bounds[1],5).tolist()}\","
        f"\"{np.round(comp.centroid,5).tolist()}\","
        f"\"{np.round(comp.extents,5).tolist()}\","
        f"{out_ply}"
    )

    canvas = Image.new("RGB", (320, 250), "white")
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), f"rank {i}: faces={len(comp.faces)}", fill=(0,0,0))
    d.text((8, 28), f"ext={np.round(comp.extents,2).tolist()}", fill=(80,80,80))
    im = Image.open(out_png).convert("RGB")
    im.thumbnail((290, 180))
    canvas.paste(im, ((320-im.width)//2, 58))
    cards.append(canvas)

cols = 4
rows = max(1, (len(cards)+cols-1)//cols)
sheet = Image.new("RGB", (320*cols, 250*rows), "white")
for i, c in enumerate(cards):
    sheet.paste(c, ((i%cols)*320, (i//cols)*250))

out_sheet = out_dir / f"{args.run_id}_hunyuan_components_sheet.jpg"
sheet.save(out_sheet, quality=95)
print("[OK] wrote", out_sheet)
