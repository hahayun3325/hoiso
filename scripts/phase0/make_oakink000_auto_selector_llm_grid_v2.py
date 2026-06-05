from pathlib import Path
from PIL import Image, ImageDraw
import re
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HOME = Path.home()

runs = [
    ("oakink000_gemini31pro_short", "gemini-3.1-pro"),
    ("oakink000_sonnet46thinking_short", "sonnet-4.6-thinking"),
    ("oakink000_gpt55_short", "gpt-5.5"),
    ("oakink000_gpt55thinking_short", "gpt-5.5-thinking"),
]

out_dir = HOME / "foho_phase0/inspection/oakink_000/auto_selector_llm_grid_v2"
out_dir.mkdir(parents=True, exist_ok=True)

def find_first(paths):
    for p in paths:
        p = Path(p)
        if p.exists():
            return p
    return None

def parse_decision(base_id):
    log = HOME / "foho_phase0/logs" / f"{base_id}_selector_auto_frag_final.log"
    if not log.exists():
        return {"before": "?", "current": "?", "selected": "missing", "status": "missing log"}

    text = log.read_text(errors="ignore")
    m = re.findall(
        r"before_frag=([0-9.]+), current_frag=([0-9.]+), margin=([0-9.]+), selected=([A-Za-z0-9_]+)",
        text,
    )
    bad = re.search(r"before_frag=999|referenced before assignment", text)

    if not m:
        return {"before": "?", "current": "?", "selected": "missing", "status": "missing line"}

    before, current, margin, selected = m[-1]
    return {
        "before": before,
        "current": current,
        "selected": selected,
        "status": "BAD fallback" if bad else "OK",
    }

def card(title, subtitle, path=None, decision=None):
    W, H = 430, 330
    canvas = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(canvas)
    d.text((10, 8), title[:60], fill=(0, 0, 0))
    d.text((10, 30), subtitle[:70], fill=(70, 70, 70))

    if decision is not None:
        y = 80
        d.text((25, y), f"before_frag: {decision['before']}", fill=(0, 0, 0)); y += 28
        d.text((25, y), f"current_frag: {decision['current']}", fill=(0, 0, 0)); y += 28

        selected_text = f"selected: {decision['selected']}"
        d.text((25, y), selected_text, fill=(0, 0, 0))
        d.ellipse((15, y - 10, 350, y + 28), outline=(220, 0, 0), width=4)
        y += 42

        color = (0, 130, 0) if decision["status"] == "OK" else (220, 0, 0)
        d.text((25, y), f"status: {decision['status']}", fill=color)
        return canvas

    if path is None or not Path(path).exists():
        d.text((160, 155), "MISSING", fill=(200, 0, 0))
        return canvas

    im = Image.open(path).convert("RGB")
    im.thumbnail((400, 250))
    canvas.paste(im, ((W - im.width) // 2, 65))
    d.text((10, 310), Path(path).name[:60], fill=(90, 90, 90))
    return canvas

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def sample_mesh(mesh, n=12000):
    try:
        pts, _ = trimesh.sample.sample_surface(mesh, min(n, max(len(mesh.faces), 1)))
        return pts
    except Exception:
        return np.asarray(mesh.vertices)

def render_scene(obj_path, hand_path, out_path):
    if obj_path is None or hand_path is None:
        return None

    obj = load_mesh(obj_path)
    hand = load_mesh(hand_path)

    obj_pts = sample_mesh(obj, 12000)
    hand_pts = sample_mesh(hand, 8000)

    pts_all = np.vstack([obj_pts, hand_pts])
    center = pts_all.mean(axis=0)
    scale = np.max(np.linalg.norm(pts_all - center, axis=1))
    if scale <= 0:
        scale = 1.0

    obj_pts = (obj_pts - center) / scale
    hand_pts = (hand_pts - center) / scale

    fig = plt.figure(figsize=(5, 4), dpi=160)
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(obj_pts[:, 0], obj_pts[:, 1], obj_pts[:, 2], s=0.15, c="0.25")
    ax.scatter(hand_pts[:, 0], hand_pts[:, 1], hand_pts[:, 2], s=0.15, c="green")
    ax.view_init(elev=15, azim=-70)
    ax.set_axis_off()
    ax.set_box_aspect([1, 1, 1])
    plt.tight_layout(pad=0)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path

def find_final_meshes(auto_run):
    ply_files = list(auto_run.rglob("*.ply"))

    obj_patterns = ["oakink_obj.ply", "test_obj.ply", "final_obj", "_obj.ply"]
    hand_patterns = ["oakink_hand.ply", "test_hand.ply", "final_hand", "_hand.ply"]

    obj = None
    hand = None

    for p in ply_files:
        name = p.name.lower()
        if "hunyuan" in str(p).lower():
            continue
        if any(x in name for x in obj_patterns):
            obj = p
            break

    for p in ply_files:
        name = p.name.lower()
        if "hunyuan" in str(p).lower():
            continue
        if any(x in name for x in hand_patterns):
            hand = p
            break

    return obj, hand

rows = []
for base_id, llm in runs:
    base_run = HOME / "foho_phase0/runs" / base_id
    auto_id = f"{base_id}_selector_auto_frag_final"
    auto_run = HOME / "foho_phase0/runs" / auto_id
    inspect_run = HOME / "foho_phase0/inspection/oakink_000" / auto_id

    crop = find_first([
        auto_run / "cropped_hoi_imgs/oakink_cropped_hoi_1.png",
        base_run / "cropped_hoi_imgs/oakink_cropped_hoi_1.png",
    ])

    inpaint = find_first([
        auto_run / "ours_inpaint/oakink_inpainted_object.png",
        base_run / "ours_inpaint/oakink_inpainted_object.png",
    ])

    debug_panel = find_first([
        inspect_run / "internal_selector_debug/internal_selector_debug_panel.jpg",
    ])

    obj, hand = find_final_meshes(auto_run)
    final_render = out_dir / f"{auto_id}_final_scene.png"
    final_render = render_scene(obj, hand, final_render)

    decision = parse_decision(base_id)

    rows.append([
        card(f"{llm}: crop", "cropped HOI input", crop),
        card(f"{llm}: inpaint", "LLM prompt + FLUX", inpaint),
        card(f"{llm}: selector decision", "red circle = final decision", decision=decision),
        card(f"{llm}: candidates", "debug exports after selector", debug_panel),
        card(f"{llm}: final scene", "rendered from final hand/object meshes", final_render),
    ])

cols = 5
cell_w, cell_h = 430, 330
sheet = Image.new("RGB", (cols * cell_w, len(rows) * cell_h + 70), "white")
d = ImageDraw.Draw(sheet)
d.text((10, 10), "OakInk split000 — LLM prompt comparison with automatic internal selector", fill=(0, 0, 0))
d.text((10, 35), "Columns: crop | inpaint | selector decision | selector debug candidates | final scene", fill=(70, 70, 70))

for r, row in enumerate(rows):
    for c, im in enumerate(row):
        sheet.paste(im, (c * cell_w, 70 + r * cell_h))

out = HOME / "foho_phase0/inspection/oakink_000/oakink000_auto_selector_llm_grid_v2.jpg"
sheet.save(out, quality=95)
print("[OK] wrote", out)
