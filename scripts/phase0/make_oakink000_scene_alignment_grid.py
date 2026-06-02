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
out_dir = Path.home() / f"foho_phase0/inspection/oakink_000/llm_scene_alignment_{args.tag}"
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

def set_color(mesh, rgba):
    mesh = mesh.copy()
    mesh.visual.face_colors = rgba
    return mesh

def render_scene(obj_path=None, hand_path=None, out_name="scene.png"):
    scene = trimesh.Scene()

    if obj_path and Path(obj_path).exists():
        obj = set_color(load_mesh(obj_path), [80, 80, 80, 255])
        scene.add_geometry(obj, geom_name="object")

    if hand_path and Path(hand_path).exists():
        hand = set_color(load_mesh(hand_path), [0, 220, 0, 255])
        scene.add_geometry(hand, geom_name="hand")

    out = out_dir / out_name
    out.write_bytes(scene.save_image(resolution=(850, 650)))
    return out

def score(path):
    if path is None or not Path(path).exists():
        return "missing"
    mesh = load_mesh(path)
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0.0
    frag = (len(comps) - 1) + (1.0 - largest)
    return f"comp={len(comps)}, frag={frag:.2f}"

def make_img_card(path, title, subtitle):
    canvas = Image.new("RGB", (360, 280), "white")
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), title[:45], fill=(0,0,0))
    d.text((8, 28), subtitle[:55], fill=(80,80,80))

    if path and Path(path).exists():
        im = Image.open(path).convert("RGB")
        im.thumbnail((330, 210))
        canvas.paste(im, ((360 - im.width)//2, 58))
    else:
        d.text((20, 130), "MISSING", fill=(180,0,0))

    return canvas

rows = []

for _, r in df.iterrows():
    run_id = r["run_id"]
    run = runs_root / run_id

    inpaint = first(run, ["ours_inpaint/*inpainted*.png"])
    initial_obj = first(run, ["hunyuan_hoi_out/*hoi*.ply", "hunyuan_hoi_out/*.ply"])
    final_obj = first(run, ["guidance_out/*obj*.ply", "guidance_out/test_obj.ply"])
    final_hand = first(run, ["guidance_out/*hand*.ply", "guidance_out/test_hand.ply"])
    selected_obj = first(run, ["fallback_out/selected_obj.ply"])
    selected_hand = first(run, ["fallback_out/selected_hand.ply"])

    report = run / "fallback_out/fallback_report.json"
    selected = ""
    if report.exists():
        try:
            selected = json.loads(report.read_text()).get("selected", "")
        except Exception:
            selected = "parse_error"

    # For Hunyuan initial scene, use initial object with final hand only for visual comparison.
    initial_scene = render_scene(initial_obj, final_hand, f"{run_id}_initial_obj_plus_final_hand.png")
    final_scene = render_scene(final_obj, final_hand, f"{run_id}_final_scene.png")
    selector_scene = render_scene(selected_obj, selected_hand, f"{run_id}_selector_scene.png")

    rows.extend([
        make_img_card(inpaint, f"{r['llm']}", "inpaint"),
        make_img_card(initial_scene, f"{r['llm']}", f"Hunyuan+hand; {score(initial_obj)}"),
        make_img_card(final_scene, f"{r['llm']}", f"final scene; {score(final_obj)}"),
        make_img_card(selector_scene, f"{r['llm']}", f"selected={selected}; {score(selected_obj)}"),
    ])

cols = 4
sheet_rows = max(1, (len(rows) + cols - 1) // cols)
sheet = Image.new("RGB", (360 * cols, 280 * sheet_rows + 70), "white")
d = ImageDraw.Draw(sheet)
d.text((10, 10), f"OakInk split000 LLM prompt comparison: {args.tag}", fill=(0,0,0))
d.text((10, 34), "Columns per LLM: inpaint | Hunyuan initial object + hand | final scene | selector scene", fill=(70,70,70))

for i, card in enumerate(rows):
    sheet.paste(card, ((i % cols) * 360, 70 + (i // cols) * 280))

out = out_dir / f"oakink000_llm_scene_alignment_grid_{args.tag}.jpg"
sheet.save(out, quality=95)
print("[OK] wrote", out)
