from pathlib import Path
import argparse
import json
import numpy as np
import trimesh
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("--run_id", required=True)
ap.add_argument("--debug_dir", required=True)
ap.add_argument("--mock_selector_dir", default="")
ap.add_argument("--out", required=True)
args = ap.parse_args()

run = Path.home() / f"foho_phase0/runs/{args.run_id}"
debug_dir = Path(args.debug_dir).expanduser()
out_path = Path(args.out).expanduser()
out_path.parent.mkdir(parents=True, exist_ok=True)

mock_dir = Path(args.mock_selector_dir).expanduser() if args.mock_selector_dir else None

def first(paths):
    for p in paths:
        p = Path(p)
        if p.exists():
            return p
    return None

def first_glob(base, patterns):
    for pat in patterns:
        hits = sorted(base.glob(pat))
        if hits:
            return hits[0]
    return None

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def score_mesh(path):
    if path is None or not Path(path).exists():
        return "missing"
    mesh = load_mesh(path)
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0.0
    frag = (len(comps) - 1) + (1.0 - largest)
    return f"comp={len(comps)}, frag={frag:.2f}"

def render_mesh(path, out_png):
    mesh = load_mesh(path)
    scene = mesh.scene()
    out_png.write_bytes(scene.save_image(resolution=(900, 700)))

def card(title, subtitle, path, is_mesh=False):
    canvas = Image.new("RGB", (360, 290), "white")
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), title[:45], fill=(0,0,0))
    d.text((8, 30), subtitle[:55], fill=(80,80,80))

    if path is None or not Path(path).exists():
        d.text((30, 140), "MISSING", fill=(180,0,0))
        return canvas

    use_path = Path(path)
    if is_mesh:
        render_dir = out_path.parent / "renders"
        render_dir.mkdir(parents=True, exist_ok=True)
        use_path = render_dir / (Path(path).stem + ".png")
        render_mesh(path, use_path)

    im = Image.open(use_path).convert("RGB")
    im.thumbnail((330, 220))
    canvas.paste(im, ((360-im.width)//2, 58))
    d.text((8, 266), Path(path).name[:45], fill=(90,90,90))
    return canvas

input_img = first([
    run / "original_imgs/oakink_full_image_1.png",
    Path.home() / "foho_phase0/inputs/oakink/oakink_split000.png",
])
inpaint = first_glob(run, ["ours_inpaint/*inpainted*.png"])
hunyuan = first_glob(run, ["hunyuan_hoi_out/*hoi*.ply", "hunyuan_hoi_out/*.ply"])
final_obj = first_glob(run, ["guidance_out/*obj*.ply", "guidance_out/test_obj.ply"])

phase42 = first_glob(debug_dir, [
    "phase42_obj_transformed_before_joint_t4_opt0.ply",
    "phase42_obj_transformed_before_joint_t5_opt0.ply",
    "phase42_obj_transformed_before_joint*.ply",
])

mock_selected = None
mock_report_text = ""
if mock_dir:
    mock_selected = mock_dir / "selected_phase42_object.ply"
    report = mock_dir / "phase42_object_selection_report.json"
    if report.exists():
        rep = json.loads(report.read_text())
        mock_report_text = "selected=" + rep.get("selected_name", "")

cards = [
    card("1. Input", "OakInk split000", input_img, False),
    card("2. Inpaint", "GPT-5.4-thinking short prompt", inpaint, False),
    card("3. Hunyuan initial", score_mesh(hunyuan), hunyuan, True),
    card("4. Phase 4.2 candidate", score_mesh(phase42), phase42, True),
    card("5. Final guided object", score_mesh(final_obj), final_obj, True),
    card("6. Mock selector choice", mock_report_text + "; " + score_mesh(mock_selected), mock_selected, True),
]

cols = 3
rows = 2
sheet = Image.new("RGB", (360*cols, 290*rows + 70), "white")
d = ImageDraw.Draw(sheet)
d.text((10, 10), f"Why internal selector is needed: {args.run_id}", fill=(0,0,0))
d.text((10, 34), "If Phase 4.2 candidate is fragmented, selector should choose an earlier trusted object candidate before alignment.", fill=(80,80,80))

for i, c in enumerate(cards):
    sheet.paste(c, ((i % cols)*360, 70 + (i // cols)*290))

sheet.save(out_path, quality=95)
print("[OK] wrote", out_path)
