from pathlib import Path
from PIL import Image, ImageDraw
import trimesh
import json

RUN_ID = "oakink000_gpt54thinking_template"
run = Path.home() / f"foho_phase0/runs/{RUN_ID}"
out_dir = Path.home() / f"foho_phase0/inspection/oakink_000/{RUN_ID}"
out_dir.mkdir(parents=True, exist_ok=True)

def first(patterns):
    for pat in patterns:
        hits = sorted(run.glob(pat))
        if hits:
            return hits[0]
    return None

def render_mesh(path, name):
    path = Path(path)
    out = out_dir / f"{name}.png"
    mesh = trimesh.load(path, process=False)
    scene = mesh if isinstance(mesh, trimesh.Scene) else mesh.scene()
    out.write_bytes(scene.save_image(resolution=(800, 650)))
    return out

def card(title, subtitle, path=None, is_mesh=False):
    canvas = Image.new("RGB", (330, 260), "white")
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), title[:45], fill=(0,0,0))
    d.text((8, 28), subtitle[:50], fill=(80,80,80))

    if path is None or not Path(path).exists():
        d.text((20, 125), "MISSING", fill=(180,0,0))
        return canvas

    try:
        use_path = path
        if is_mesh:
            use_path = render_mesh(path, title.replace(" ", "_").replace("/", "_"))

        im = Image.open(use_path).convert("RGB")
        im.thumbnail((300, 190))
        canvas.paste(im, ((330-im.width)//2, 58))
        d.text((8, 238), Path(path).name[:44], fill=(80,80,80))
    except Exception as e:
        d.text((20, 110), f"ERROR\n{e}", fill=(180,0,0))

    return canvas

items = [
    ("1. RGB input", "official/copy input", run / "original_imgs/oakink_full_image_1.png", False),
    ("2. HOI crop", "detector crop", run / "cropped_hoi_imgs/oakink_cropped_hoi_1.png", False),
    ("3. Crop w/o bg", "segmentation result", run / "cropped_hoi_imgs_wo_bckg/oakink_cropped_hoi_wo_bckg_1.png", False),
    ("4. Object mask", "segmentation mask", run / "cropped_hand_masks/oakink_cropped_obj_mask.png", False),
    ("5. Hand mask", "segmentation mask", run / "cropped_hand_masks/oakink_cropped_hand_mask.png", False),
    ("6. MoGe depth", "geometry prior", run / "moge_out/oakink_cropped_hoi/depth_vis.png", False),
    ("7. MoGe normal", "geometry prior", run / "moge_out/oakink_cropped_hoi/normal.png", False),
    ("8. Inpaint", "FLUX with LLM prompt", run / "ours_inpaint/oakink_inpainted_object.png", False),
    ("9. Hunyuan initial", "3D object prior", run / "hunyuan_hoi_out/oakink_hoi_mesh.ply", True),
    ("10. Final object", "rectified-flow guidance", run / "guidance_out/oakink_obj.ply", True),
    ("11. Final hand", "guided hand", run / "guidance_out/oakink_hand.ply", True),
    ("12. Selector output", "selected object", run / "fallback_out/selected_obj.ply", True),
]

cards = [card(*x) for x in items]

cols = 4
rows = (len(cards) + cols - 1) // cols
sheet = Image.new("RGB", (330*cols, 260*rows + 70), "white")
d = ImageDraw.Draw(sheet)
d.text((10, 10), f"Pipeline order: {RUN_ID}", fill=(0,0,0))

selected = ""
report = run / "fallback_out/fallback_report.json"
if report.exists():
    try:
        selected = json.loads(report.read_text()).get("selected", "")
    except Exception:
        pass

d.text((10, 34), f"Detection/crop fixed; LLM prompt changes inpainting/reconstruction. Selector selected: {selected}", fill=(70,70,70))

for i, c in enumerate(cards):
    sheet.paste(c, ((i % cols)*330, 70 + (i // cols)*260))

out = out_dir / f"{RUN_ID}_pipeline_ordered_sheet.jpg"
sheet.save(out, quality=95)
print("[OK] wrote", out)
