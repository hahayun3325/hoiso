from pathlib import Path
import argparse
import numpy as np
import trimesh
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("--run_id", required=True)
ap.add_argument("--mesh_name", default="oakink_hoi_mesh.ply")
args = ap.parse_args()

run = Path.home() / f"foho_phase0/runs/{args.run_id}"
mesh_path = run / "hunyuan_hoi_out" / args.mesh_name
out_dir = Path.home() / f"foho_phase0/inspection/oakink_000/{args.run_id}/selector_component_debug"
out_dir.mkdir(parents=True, exist_ok=True)

if not mesh_path.exists():
    raise FileNotFoundError(mesh_path)

mesh = trimesh.load(mesh_path, process=False)
if isinstance(mesh, trimesh.Scene):
    mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))

components = sorted(
    mesh.split(only_watertight=False),
    key=lambda m: len(m.faces),
    reverse=True,
)

rows = []
cards = []

for i, comp in enumerate(components):
    ply = out_dir / f"component_rank{i}.ply"
    png = out_dir / f"component_rank{i}.png"
    comp.export(ply)
    png.write_bytes(comp.scene().save_image(resolution=(800, 650)))

    rows.append({
        "rank": i,
        "vertices": len(comp.vertices),
        "faces": len(comp.faces),
        "bounds_min": np.round(comp.bounds[0], 5).tolist(),
        "bounds_max": np.round(comp.bounds[1], 5).tolist(),
        "center": np.round(comp.centroid, 5).tolist(),
        "extents": np.round(comp.extents, 5).tolist(),
        "ply": str(ply),
    })

    canvas = Image.new("RGB", (360, 280), "white")
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), f"rank {i}: faces={len(comp.faces)}", fill=(0,0,0))
    d.text((8, 28), f"ext={np.round(comp.extents, 2).tolist()}", fill=(80,80,80))

    im = Image.open(png).convert("RGB")
    im.thumbnail((330, 210))
    canvas.paste(im, ((360 - im.width)//2, 58))
    cards.append(canvas)

cols = 3
sheet_rows = max(1, (len(cards) + cols - 1) // cols)
sheet = Image.new("RGB", (360 * cols, 280 * sheet_rows), "white")
for i, c in enumerate(cards):
    sheet.paste(c, ((i % cols) * 360, (i // cols) * 280))

sheet_path = out_dir / f"{args.run_id}_selector_component_debug_sheet.jpg"
sheet.save(sheet_path, quality=95)

csv_path = out_dir / "component_summary.csv"
with csv_path.open("w") as f:
    f.write("rank,vertices,faces,bounds_min,bounds_max,center,extents,ply\n")
    for r in rows:
        f.write(
            f"{r['rank']},{r['vertices']},{r['faces']},"
            f"\"{r['bounds_min']}\",\"{r['bounds_max']}\","
            f"\"{r['center']}\",\"{r['extents']}\",\"{r['ply']}\"\n"
        )

print("[OK] wrote", sheet_path)
print("[OK] wrote", csv_path)
