from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
import trimesh
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("--base_run_id", required=True)
ap.add_argument("--debug_run_id", required=True)
ap.add_argument("--debug_dir", required=True)
ap.add_argument("--mock_selector_dir", required=True)
ap.add_argument("--csv", default="docs/phase0/manual_llm_prompts/oakink000_prompt_candidates_short.csv")
ap.add_argument("--out", required=True)
args = ap.parse_args()

base_run = Path.home() / "foho_phase0/runs" / args.base_run_id
debug_run = Path.home() / "foho_phase0/runs" / args.debug_run_id
debug_dir = Path(args.debug_dir).expanduser()
mock_dir = Path(args.mock_selector_dir).expanduser()
out_path = Path(args.out).expanduser()
out_path.parent.mkdir(parents=True, exist_ok=True)

render_dir = out_path.parent / "candidate_full_panel_renders"
render_dir.mkdir(parents=True, exist_ok=True)

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

def color_mesh(mesh, rgba):
    mesh = mesh.copy()
    mesh.visual.face_colors = rgba
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

def render_mesh(path, name):
    out = render_dir / f"{name}.png"
    mesh = load_mesh(path)
    out.write_bytes(mesh.scene().save_image(resolution=(900, 700)))
    return out

def render_scene(obj_path, hand_path, name):
    out = render_dir / f"{name}.png"
    scene = trimesh.Scene()
    if obj_path and Path(obj_path).exists():
        scene.add_geometry(color_mesh(load_mesh(obj_path), [80, 80, 80, 255]), geom_name="object")
    if hand_path and Path(hand_path).exists():
        scene.add_geometry(color_mesh(load_mesh(hand_path), [0, 220, 0, 255]), geom_name="hand")
    out.write_bytes(scene.save_image(resolution=(900, 700)))
    return out

def img_card(title, subtitle, path, is_mesh=False):
    canvas = Image.new("RGB", (390, 310), "white")
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), title[:48], fill=(0, 0, 0))
    d.text((8, 30), subtitle[:60], fill=(80, 80, 80))

    if path is None or not Path(path).exists():
        d.text((35, 150), "MISSING", fill=(180, 0, 0))
        return canvas

    use_path = Path(path)
    if is_mesh:
        use_path = render_mesh(path, title.replace(" ", "_").replace("/", "_"))

    im = Image.open(use_path).convert("RGB")
    im.thumbnail((360, 235))
    canvas.paste(im, ((390 - im.width) // 2, 62))
    d.text((8, 292), Path(path).name[:55], fill=(90, 90, 90))
    return canvas

# Read LLM label.
llm_name = args.base_run_id
prompt_text = ""
csv_path = Path(args.csv)
if csv_path.exists():
    df = pd.read_csv(csv_path)
    hit = df[df["run_id"] == args.base_run_id]
    if len(hit):
        llm_name = str(hit.iloc[0]["llm"])
        prompt_text = str(hit.iloc[0]["response"])

# Main assets.
input_img = debug_run / "original_imgs/oakink_full_image_1.png"
inpaint = first_glob(debug_run, ["ours_inpaint/*inpainted*.png"])
hunyuan_full = first_glob(debug_run, ["hunyuan_hoi_out/*hoi*.ply", "hunyuan_hoi_out/*.ply"])
phase42 = first_glob(debug_dir, [
    "phase42_obj_transformed_before_joint_t4_opt0.ply",
    "phase42_obj_transformed_before_joint_t5_opt0.ply",
    "phase42_obj_transformed_before_joint*.ply",
])
final_obj = first_glob(debug_run, ["guidance_out/*obj*.ply", "guidance_out/test_obj.ply"])
final_hand = first_glob(debug_run, ["guidance_out/*hand*.ply", "guidance_out/test_hand.ply"])
mock_selected = mock_dir / "selected_phase42_object.ply"

# Hunyuan component candidates.
cand_dir = mock_dir.parent / "object_only_candidates"
hunyuan_r0 = cand_dir / "hunyuan_component_rank0_candidate.ply"
hunyuan_r1 = cand_dir / "hunyuan_component_rank1_candidate.ply"
hunyuan_r2 = cand_dir / "hunyuan_component_rank2_candidate.ply"

# Mock decision.
decision = ""
report = mock_dir / "phase42_object_selection_report.json"
if report.exists():
    try:
        decision = json.loads(report.read_text()).get("selected_name", "")
    except Exception:
        decision = "parse_error"

final_scene = None
if final_obj and final_hand:
    final_scene = render_scene(final_obj, final_hand, "final_obj_plus_final_hand")

cards = [
    img_card("1. Input", "OakInk split000", input_img),
    img_card("2. Inpaint", f"{llm_name}", inpaint),
    img_card("3. Hunyuan full HOI", score_mesh(hunyuan_full), hunyuan_full, True),
    img_card("4. Hunyuan rank0", score_mesh(hunyuan_r0), hunyuan_r0, True),
    img_card("5. Hunyuan rank1", score_mesh(hunyuan_r1), hunyuan_r1, True),
    img_card("6. Hunyuan rank2", score_mesh(hunyuan_r2), hunyuan_r2, True),
    img_card("7. Phase 4.2 candidate", score_mesh(phase42), phase42, True),
    img_card("8. Final guided object", score_mesh(final_obj), final_obj, True),
    img_card("9. Final pipeline scene", "final object + final hand", final_scene),
    img_card("10. Mock selector choice", f"selected={decision}; {score_mesh(mock_selected)}", mock_selected, True),
]

cols = 5
rows = (len(cards) + cols - 1) // cols
sheet = Image.new("RGB", (390 * cols, 310 * rows + 95), "white")
d = ImageDraw.Draw(sheet)
d.text((10, 10), f"Selector candidate comparison: {args.base_run_id}", fill=(0, 0, 0))
d.text((10, 34), f"LLM: {llm_name}", fill=(60, 60, 60))
d.text((10, 58), "Shows all candidate object poses plus final pipeline scene.", fill=(60, 60, 60))

for i, c in enumerate(cards):
    sheet.paste(c, ((i % cols) * 390, 95 + (i // cols) * 310))

sheet.save(out_path, quality=95)
print("[OK] wrote", out_path)
