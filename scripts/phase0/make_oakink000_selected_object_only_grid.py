from pathlib import Path
import argparse
import json
import pandas as pd
import trimesh
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("--csv", required=True)
ap.add_argument("--tag", default="short")
args = ap.parse_args()

df = pd.read_csv(args.csv)
runs_root = Path.home() / "foho_phase0/runs"
out_dir = Path.home() / f"foho_phase0/inspection/oakink_000/selected_object_only_{args.tag}"
out_dir.mkdir(parents=True, exist_ok=True)

def first(run, patterns):
    for pat in patterns:
        hits = sorted(run.glob(pat))
        if hits:
            return hits[0]
    return None

def render_mesh(path, out_png):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    scene = mesh.scene()
    out_png.write_bytes(scene.save_image(resolution=(800, 650)))

cards = []

for _, r in df.iterrows():
    run = runs_root / r["run_id"]
    selected_obj = first(run, ["fallback_out/selected_obj.ply"])

    decision = ""
    report = run / "fallback_out/fallback_report.json"
    if report.exists():
        try:
            decision = json.loads(report.read_text()).get("selected", "")
        except Exception:
            decision = "parse_error"

    render_png = None
    if selected_obj and Path(selected_obj).exists():
        render_png = out_dir / f"{r['run_id']}_selected_obj.png"
        render_mesh(selected_obj, render_png)

    canvas = Image.new("RGB", (360, 290), "white")
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), str(r["llm"])[:42], fill=(0,0,0))
    d.text((8, 30), f"selected={decision}", fill=(80,80,80))

    if render_png and render_png.exists():
        im = Image.open(render_png).convert("RGB")
        im.thumbnail((330, 220))
        canvas.paste(im, ((360-im.width)//2, 58))
    else:
        d.text((30, 140), "MISSING", fill=(180,0,0))

    cards.append(canvas)

cols = 4
rows = max(1, (len(cards)+cols-1)//cols)
sheet = Image.new("RGB", (360*cols, 290*rows + 60), "white")
d = ImageDraw.Draw(sheet)
d.text((10, 10), f"OakInk split000 selected object only ({args.tag})", fill=(0,0,0))
d.text((10, 32), "This avoids hand overlay and shows only the object source selected by the selector.", fill=(80,80,80))

for i, c in enumerate(cards):
    sheet.paste(c, ((i%cols)*360, 60 + (i//cols)*290))

out = out_dir / f"oakink000_selected_object_only_grid_{args.tag}.jpg"
sheet.save(out, quality=95)
print("[OK] wrote", out)
