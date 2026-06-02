from pathlib import Path
import argparse
import json
import numpy as np
import trimesh
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("--run_id", required=True)
args = ap.parse_args()

run = Path.home() / f"foho_phase0/runs/{args.run_id}"
out_dir = Path.home() / f"foho_phase0/inspection/oakink_000/{args.run_id}/alignment_diagnosis"
out_dir.mkdir(parents=True, exist_ok=True)

def first(patterns):
    for pat in patterns:
        hits = sorted(run.glob(pat))
        if hits:
            return hits[0]
    return None

def load(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def color(mesh, rgba):
    mesh = mesh.copy()
    mesh.visual.face_colors = rgba
    return mesh

obj_paths = {
    "initial_obj": first(["hunyuan_hoi_out/*hoi*.ply", "hunyuan_hoi_out/*.ply"]),
    "final_obj": first(["guidance_out/*obj*.ply", "guidance_out/test_obj.ply"]),
    "selected_obj": first(["fallback_out/selected_obj.ply"]),
}
hand_paths = {
    "final_hand": first(["guidance_out/*hand*.ply", "guidance_out/test_hand.ply"]),
    "selected_hand": first(["fallback_out/selected_hand.ply"]),
}

print("===== paths =====")
for k, v in {**obj_paths, **hand_paths}.items():
    print(k, v)

print("\n===== bounds / centers =====")
for k, p in {**obj_paths, **hand_paths}.items():
    if p is None or not Path(p).exists():
        continue
    m = load(p)
    print(k)
    print("  bounds:", m.bounds.tolist())
    print("  center:", m.centroid.tolist())
    print("  extents:", m.extents.tolist())

def render_pair(obj_name, hand_name):
    obj = obj_paths[obj_name]
    hand = hand_paths[hand_name]
    if obj is None or hand is None:
        return None

    scene = trimesh.Scene()
    scene.add_geometry(color(load(obj), [90, 90, 90, 255]), geom_name=obj_name)
    scene.add_geometry(color(load(hand), [0, 220, 0, 255]), geom_name=hand_name)

    out_glb = out_dir / f"{obj_name}_{hand_name}.glb"
    out_png = out_dir / f"{obj_name}_{hand_name}.png"
    scene.export(out_glb)
    out_png.write_bytes(scene.save_image(resolution=(1000, 800)))
    return out_png

cards = []
for obj_name, hand_name in [
    ("initial_obj", "final_hand"),
    ("final_obj", "final_hand"),
    ("selected_obj", "selected_hand"),
]:
    png = render_pair(obj_name, hand_name)

    canvas = Image.new("RGB", (400, 320), "white")
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), f"{obj_name} + {hand_name}", fill=(0,0,0))
    if png and png.exists():
        im = Image.open(png).convert("RGB")
        im.thumbnail((370, 250))
        canvas.paste(im, ((400-im.width)//2, 50))
    else:
        d.text((30, 150), "MISSING", fill=(180,0,0))
    cards.append(canvas)

sheet = Image.new("RGB", (400 * len(cards), 320), "white")
for i, c in enumerate(cards):
    sheet.paste(c, (400*i, 0))

out = out_dir / f"{args.run_id}_alignment_diagnosis_sheet.jpg"
sheet.save(out, quality=95)
print("[OK] wrote", out)
