from pathlib import Path
from PIL import Image, ImageDraw
import re
import trimesh
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HOME = Path.home()
SUFFIX = "selector_auto_frag_export_v4_final"

runs = [
    ("oakink000_gemini31pro_short", "gemini-3.1-pro"),
    ("oakink000_sonnet46thinking_short", "sonnet-4.6-thinking"),
    ("oakink000_gpt55_short", "gpt-5.5"),
    ("oakink000_gpt55thinking_short", "gpt-5.5-thinking"),
]

def find_first(root, patterns):
    root = Path(root)
    for pat in patterns:
        hits = sorted(root.glob(pat))
        if hits:
            return hits[0]
    return None

def parse_decision(run_id):
    log = HOME / "foho_phase0/logs" / f"{run_id}.log"
    text = log.read_text(errors="ignore") if log.exists() else ""
    m = re.findall(
        r"before_frag=([0-9.]+), current_frag=([0-9.]+), margin=([0-9.]+), selected=([A-Za-z0-9_]+)",
        text,
    )
    if not m:
        return "before=?\nafter=?\nselected=missing", "missing"
    before, current, margin, selected = m[-1]
    return f"before={before}\nafter={current}\nselected={selected}", selected

def render_mesh(mesh_paths, out_png, title="", colors=None):
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)

    if colors is None:
        colors = ["0.2", "green"]

    fig = plt.figure(figsize=(3.4, 2.8))
    ax = fig.add_subplot(111, projection="3d")
    all_pts = []

    for idx, path in enumerate(mesh_paths):
        if path is None or not Path(path).exists():
            continue
        mesh = trimesh.load(path, process=False)
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
        if len(mesh.vertices) == 0:
            continue

        pts = mesh.vertices
        if len(pts) > 6000:
            rng = np.random.default_rng(0)
            pts = pts[rng.choice(len(pts), 6000, replace=False)]

        all_pts.append(pts)
        ax.scatter(
            pts[:, 0], pts[:, 1], pts[:, 2],
            s=0.35,
            c=colors[min(idx, len(colors) - 1)],
            alpha=0.85,
        )

    if all_pts:
        pts = np.concatenate(all_pts, axis=0)
        center = pts.mean(axis=0)
        radius = max(np.max(np.linalg.norm(pts - center, axis=1)), 1e-6)
        ax.set_xlim(center[0] - radius, center[0] + radius)
        ax.set_ylim(center[1] - radius, center[1] + radius)
        ax.set_zlim(center[2] - radius, center[2] + radius)

    ax.view_init(elev=15, azim=-70)
    ax.set_axis_off()
    ax.set_title(title, fontsize=8)
    plt.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)

def cell_from_image(path, label, size=(320, 245), red=False):
    canvas = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 8), label, fill=(0, 0, 0))

    if path is None or not Path(path).exists():
        draw.text((80, 115), "MISSING", fill=(180, 0, 0))
    else:
        img = Image.open(path).convert("RGB")
        img.thumbnail((size[0] - 20, size[1] - 50))
        x = (size[0] - img.width) // 2
        y = 42
        canvas.paste(img, (x, y))

    if red:
        draw.rectangle([3, 3, size[0] - 4, size[1] - 4], outline=(255, 0, 0), width=5)

    return canvas

rows = []

for base_id, label in runs:
    run_id = f"{base_id}_{SUFFIX}"
    run = HOME / "foho_phase0/runs" / run_id
    debug = HOME / "foho_phase0/inspection/oakink_000" / run_id / "internal_selector_debug"
    tmp = debug / "grid_tmp"
    tmp.mkdir(parents=True, exist_ok=True)

    crop = find_first(run, ["cropped_hoi_imgs/*cropped*hoi*.png", "cropped_hoi_imgs/*.png"])
    inpaint = find_first(run, ["ours_inpaint/*inpaint*.png", "**/*inpainted*object*.png", "**/*inpaint*.png"])

    before = debug / "selector_candidate_before_phase42.ply"
    after = debug / "selector_candidate_phase42_before_joint.ply"
    selected = debug / "selector_selected_before_joint.ply"

    final_obj = find_first(run, ["guidance_out/*obj*.ply", "guidance_out/test_obj.ply"])
    final_hand = find_first(run, ["guidance_out/*hand*.ply", "guidance_out/test_hand.ply"])

    before_png = tmp / "before.png"
    after_png = tmp / "after.png"
    selected_png = tmp / "selected.png"
    final_png = tmp / "final.png"

    decision_text, selected_name = parse_decision(run_id)

    render_mesh([before], before_png, "before 4.2")
    render_mesh([after], after_png, "after 4.2")
    render_mesh([selected], selected_png, "selected")
    render_mesh([final_obj, final_hand], final_png, "final scene", colors=["0.2", "green"])

    rows.append([
        cell_from_image(crop, f"{label}\n1 crop"),
        cell_from_image(inpaint, "2 inpaint"),
        cell_from_image(before_png, f"3 before 4.2\n{decision_text}", red=(selected_name == "before_phase42")),
        cell_from_image(after_png, "4 after 4.2", red=(selected_name == "phase42_before_joint")),
        cell_from_image(selected_png, "5 selected object"),
        cell_from_image(final_png, "6 final scene"),
    ])

cell_w, cell_h = rows[0][0].size
title_h = 55
panel = Image.new("RGB", (cell_w * 6, title_h + cell_h * len(rows)), "white")
draw = ImageDraw.Draw(panel)
draw.text((10, 10), "OakInk split000 — automatic internal selector LLM comparison", fill=(0, 0, 0))
draw.text((10, 30), "Red frame = selected candidate before joint alignment", fill=(180, 0, 0))

for r, row in enumerate(rows):
    for c, cell in enumerate(row):
        panel.paste(cell, (c * cell_w, title_h + r * cell_h))

out = HOME / "foho_phase0/inspection/oakink_000/oakink000_auto_selector_llm_grid_v5.jpg"
out.parent.mkdir(parents=True, exist_ok=True)
panel.save(out)
print("[OK] wrote", out)
