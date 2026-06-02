from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
import trimesh
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("--csv", required=True)
ap.add_argument("--tag", default="short")
args = ap.parse_args()

runs_root = Path.home() / "foho_phase0/runs"
out_dir = Path.home() / f"foho_phase0/inspection/oakink_000/final_selection_{args.tag}"
out_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(args.csv)

def first(run, patterns):
    for pat in patterns:
        hits = sorted(run.glob(pat))
        if hits:
            return hits[0]
    return None

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def color(mesh, rgba):
    mesh = mesh.copy()
    mesh.visual.face_colors = rgba
    return mesh

def score(path):
    if not path or not Path(path).exists():
        return "missing"
    mesh = load_mesh(path)
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0.0
    frag = (len(comps) - 1) + (1.0 - largest)
    return f"comp={len(comps)}, frag={frag:.2f}"

def render_scene(obj_path, hand_path, out_name):
    scene = trimesh.Scene()
    if obj_path and Path(obj_path).exists():
        scene.add_geometry(color(load_mesh(obj_path), [80, 80, 80, 255]), geom_name="object")
    if hand_path and Path(hand_path).exists():
        scene.add_geometry(color(load_mesh(hand_path), [0, 220, 0, 255]), geom_name="hand")
    out = out_dir / out_name
    out.write_bytes(scene.save_image(resolution=(850, 650)))
    return out

def card(title, subtitle, path):
    canvas = Image.new("RGB", (390, 310), "white")
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), title[:48], fill=(0,0,0))
    d.text((8, 30), subtitle[:60], fill=(80,80,80))
    if path and Path(path).exists():
        im = Image.open(path).convert("RGB")
        im.thumbnail((360, 240))
        canvas.paste(im, ((390-im.width)//2, 60))
    else:
        d.text((30, 150), "MISSING", fill=(180,0,0))
    return canvas

cards = []

for _, r in df.iterrows():
    run_id = r["run_id"]
    run = runs_root / run_id

    selected_obj = first(run, ["fallback_out/selected_obj.ply"])
    selected_hand = first(run, ["fallback_out/selected_hand.ply"])
    final_obj = first(run, ["guidance_out/*obj*.ply", "guidance_out/test_obj.ply"])

    report = run / "fallback_out/fallback_report.json"
    decision = ""
    if report.exists():
        try:
            decision = json.loads(report.read_text()).get("selected", "")
        except Exception:
            decision = "parse_error"

    png = render_scene(
        selected_obj,
        selected_hand,
        f"{run_id}_selected_scene.png"
    )

    subtitle = f"{decision}; {score(selected_obj)}"
    cards.append(card(str(r["llm"]), subtitle, png))

cols = 4
rows = max(1, (len(cards) + cols - 1)//cols)
sheet = Image.new("RGB", (390*cols, 310*rows + 70), "white")
d = ImageDraw.Draw(sheet)
d.text((10, 10), f"OakInk split000 final selector outputs across LLMs ({args.tag})", fill=(0,0,0))
d.text((10, 34), "Gray = selected object, green = selected hand. This shows the final post-selector result only.", fill=(70,70,70))

for i, c in enumerate(cards):
    sheet.paste(c, ((i % cols)*390, 70 + (i//cols)*310))

out = out_dir / f"oakink000_final_selection_grid_{args.tag}.jpg"
sheet.save(out, quality=95)
print("[OK] wrote", out)
