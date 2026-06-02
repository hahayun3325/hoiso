from pathlib import Path
import argparse
from PIL import Image, ImageDraw
import trimesh
import json
import numpy as np

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def render_mesh(path, out_png):
    mesh = load_mesh(path)
    scene = mesh.scene()
    out_png.write_bytes(scene.save_image(resolution=(900, 700)))

def score(path):
    mesh = load_mesh(path)
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0.0
    frag = (len(comps) - 1) + (1.0 - largest)
    return f"comp={len(comps)}, frag={frag:.3f}"

def first(run, patterns):
    for pat in patterns:
        hits = sorted(run.glob(pat))
        if hits:
            return hits[0]
    return None

ap = argparse.ArgumentParser()
ap.add_argument("--run_id", required=True)
args = ap.parse_args()

run = Path.home() / f"foho_phase0/runs/{args.run_id}"
out_dir = Path.home() / f"foho_phase0/inspection/oakink_000/{args.run_id}"
out_dir.mkdir(parents=True, exist_ok=True)

items = {
    "inpaint": first(run, ["ours_inpaint/*inpainted*.png"]),
    "hunyuan": first(run, ["hunyuan_hoi_out/*hoi*.ply", "hunyuan_hoi_out/*.ply"]),
    "final_obj": first(run, ["guidance_out/*obj*.ply", "guidance_out/test_obj.ply"]),
    "final_hand": first(run, ["guidance_out/*hand*.ply", "guidance_out/test_hand.ply"]),
    "selected_obj": first(run, ["fallback_out/selected_obj.ply"]),
    "selected_hand": first(run, ["fallback_out/selected_hand.ply"]),
}

rendered = {}

for name, path in items.items():
    if path is None or not Path(path).exists():
        print("[MISSING]", name)
        continue

    path = Path(path)
    if path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
        rendered[name] = path
    else:
        out_png = out_dir / f"{name}.png"
        render_mesh(path, out_png)
        rendered[name] = out_png
        print("[OK]", name, out_png)

# Combined fallback scene.
selected_obj = items.get("selected_obj")
selected_hand = items.get("selected_hand")
if selected_obj and selected_hand:
    scene = trimesh.Scene()
    scene.add_geometry(load_mesh(selected_obj), geom_name="selected_obj")
    scene.add_geometry(load_mesh(selected_hand), geom_name="selected_hand")
    scene_glb = run / "fallback_out/fallback_scene.glb"
    scene_png = run / "fallback_out/fallback_scene.png"
    scene.export(scene_glb)
    scene_png.write_bytes(scene.save_image(resolution=(1000, 800)))
    rendered["fallback_scene"] = scene_png
    print("[OK] wrote", scene_glb)
    print("[OK] wrote", scene_png)

report = run / "fallback_out/fallback_report.json"
selected = ""
if report.exists():
    selected = json.loads(report.read_text()).get("selected", "")

cards = []
order = [
    ("Inpainted object", "inpaint"),
    ("Hunyuan initial", "hunyuan"),
    ("Final object", "final_obj"),
    ("Selector object", "selected_obj"),
    ("Fallback scene", "fallback_scene"),
]

for title, key in order:
    canvas = Image.new("RGB", (360, 290), "white")
    d = ImageDraw.Draw(canvas)
    d.text((10, 8), title, fill=(0,0,0))

    path = rendered.get(key)
    subtitle = ""
    if key in ["hunyuan", "final_obj", "selected_obj"] and items.get(key.replace("hunyuan","hunyuan")):
        try:
            mesh_path = items["hunyuan"] if key == "hunyuan" else items[key]
            subtitle = score(mesh_path)
        except Exception:
            subtitle = ""
    if key == "selected_obj":
        subtitle = f"selected={selected}; {subtitle}"

    d.text((10, 28), subtitle[:55], fill=(80,80,80))

    if path and Path(path).exists():
        im = Image.open(path).convert("RGB")
        im.thumbnail((330, 220))
        canvas.paste(im, ((360-im.width)//2, 58))
    else:
        d.text((20, 130), "MISSING", fill=(180,0,0))

    cards.append(canvas)

sheet = Image.new("RGB", (360 * len(cards), 290), "white")
for i, c in enumerate(cards):
    sheet.paste(c, (i * 360, 0))

out_sheet = out_dir / f"{args.run_id}_selector_sheet.jpg"
sheet.save(out_sheet, quality=95)
print("[OK] wrote", out_sheet)
