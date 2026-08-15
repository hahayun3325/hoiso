from pathlib import Path
from PIL import Image, ImageDraw
import re
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HOME = Path.home()

runs = [
    ("oakink000_gemini31pro_short", "gemini-3.1-pro"),
    ("oakink000_sonnet46thinking_short", "sonnet-4.6-thinking"),
    ("oakink000_gpt55_short", "gpt-5.5"),
    ("oakink000_gpt55thinking_short", "gpt-5.5-thinking"),
]

def find_first(paths):
    for p in paths:
        p = Path(p)
        if p.exists():
            return p
    return None

def parse_decision(base_id):
    log = HOME / "foho_phase0/logs" / f"{base_id}_selector_auto_frag_final.log"
    text = log.read_text(errors="ignore") if log.exists() else ""
    m = re.findall(
        r"before_frag=([0-9.]+), current_frag=([0-9.]+), margin=([0-9.]+), selected=([A-Za-z0-9_]+)",
        text,
    )
    if not m:
        return {"before": "?", "current": "?", "selected": "missing"}
    before, current, margin, selected = m[-1]
    return {"before": before, "current": current, "selected": selected}

def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh

def render_mesh(mesh_paths, out_path, title="", azim=-70, elev=15):
    meshes = []
    for p in mesh_paths:
        if p and Path(p).exists():
            meshes.append(load_mesh(p))

    if not meshes:
        return None

    all_v = np.vstack([m.vertices for m in meshes if len(m.vertices)])
    center = all_v.mean(axis=0)
    scale = np.max(np.linalg.norm(all_v - center, axis=1))
    if scale <= 0:
        scale = 1.0

    fig = plt.figure(figsize=(4.2, 3.2), dpi=160)
    ax = fig.add_subplot(111, projection="3d")

    colors = ["0.25", "green"]
    for idx, mesh in enumerate(meshes):
        verts = (mesh.vertices - center) / scale
        faces = mesh.faces

        if len(faces) > 12000:
            keep = np.linspace(0, len(faces) - 1, 12000).astype(int)
            faces = faces[keep]

        poly = Poly3DCollection(
            verts[faces],
            facecolor=colors[min(idx, len(colors)-1)],
            edgecolor="none",
            alpha=0.95,
        )
        ax.add_collection3d(poly)

    ax.set_xlim(-0.8, 0.8)
    ax.set_ylim(-0.8, 0.8)
    ax.set_zlim(-0.8, 0.8)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_box_aspect([1, 1, 1])
    plt.tight_layout(pad=0)
    fig.savefig(out_path)
    plt.close(fig)
    return out_path

def card(title, subtitle, img_path=None, red=False):
    W, H = 390, 310
    canvas = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), title[:55], fill=(0, 0, 0))
    d.text((8, 30), subtitle[:65], fill=(70, 70, 70))

    if img_path is None or not Path(img_path).exists():
        d.text((140, 150), "MISSING", fill=(200, 0, 0))
    else:
        im = Image.open(img_path).convert("RGB")
        im.thumbnail((360, 235))
        canvas.paste(im, ((W - im.width) // 2, 58))
        d.text((8, 292), Path(img_path).name[:52], fill=(90, 90, 90))

    if red:
        d.rectangle((3, 3, W - 4, H - 4), outline=(220, 0, 0), width=6)

    return canvas

def find_candidate_meshes(base_id):
    run_id = f"{base_id}_selector_auto_frag_final"
    run_dir = HOME / "foho_phase0/runs" / run_id
    debug_dir = HOME / "foho_phase0/inspection/oakink_000" / run_id / "internal_selector_debug"

    # Preferred exact candidate names, if your patch exports them.
    before = find_first([
        debug_dir / "selector_candidate_before_phase42.ply",
        debug_dir / "before_phase42_object.ply",
        debug_dir / "before_phase42_mesh.ply",
    ])

    after = find_first([
        debug_dir / "selector_candidate_phase42_before_joint.ply",
        debug_dir / "phase42_before_joint_object.ply",
        debug_dir / "phase42_before_joint_mesh.ply",
    ])

    selected = find_first([
        debug_dir / "selector_selected_before_joint.ply",
        debug_dir / "selected_phase42_object.ply",
    ])

    # Fallback: these are not perfect candidate proof, but useful visualization.
    if after is None:
        after = find_first(sorted(debug_dir.glob("phase42_obj_transformed_before_joint_t4_opt0.ply")))

    if before is None:
        before = find_first(sorted((run_dir / "foho_debug").glob("*/debug_obj_before_hunyuan2moge.ply")))

    if selected is None:
        decision = parse_decision(base_id)["selected"]
        selected = before if decision == "before_phase42" else after

    final_obj = find_first([
        run_dir / "guidance_out/oakink_obj.ply",
        *sorted(run_dir.glob("foho_debug/*/final_obj_mesh.ply")),
    ])
    final_hand = find_first([
        run_dir / "guidance_out/oakink_hand.ply",
        *sorted(run_dir.glob("foho_debug/*/final_hand_mesh.ply")),
    ])

    return before, after, selected, final_obj, final_hand

out_root = HOME / "foho_phase0/inspection/oakink_000/auto_selector_llm_grid_v3"
out_root.mkdir(parents=True, exist_ok=True)

rows = []

for base_id, llm in runs:
    run_id = f"{base_id}_selector_auto_frag_final"
    base_run = HOME / "foho_phase0/runs" / base_id
    run_dir = HOME / "foho_phase0/runs" / run_id

    decision = parse_decision(base_id)
    before, after, selected, final_obj, final_hand = find_candidate_meshes(base_id)

    crop = find_first([
        run_dir / "cropped_hoi_imgs/oakink_cropped_hoi_1.png",
        base_run / "cropped_hoi_imgs/oakink_cropped_hoi_1.png",
    ])
    inpaint = find_first([
        run_dir / "ours_inpaint/oakink_inpainted_object.png",
        base_run / "ours_inpaint/oakink_inpainted_object.png",
    ])

    before_png = render_mesh([before], out_root / f"{run_id}_before42.png", "before42")
    after_png = render_mesh([after], out_root / f"{run_id}_after42.png", "after42")
    selected_png = render_mesh([selected], out_root / f"{run_id}_selected.png", "selected")
    final_png = render_mesh([final_obj, final_hand], out_root / f"{run_id}_final_scene.png", "final")

    rows.append([
        card(f"{llm}: crop", "input cropped HOI", crop),
        card(f"{llm}: inpaint", "LLM prompt + FLUX", inpaint),
        card(f"{llm}: before Phase 4.2", f"frag={decision['before']}", before_png, red=(decision["selected"] == "before_phase42")),
        card(f"{llm}: after Phase 4.2", f"frag={decision['current']}", after_png, red=(decision["selected"] == "phase42_before_joint")),
        card(f"{llm}: final scene", "object + hand after joint", final_png),
    ])

cell_w, cell_h = 390, 310
cols = 5
sheet = Image.new("RGB", (cols * cell_w, len(rows) * cell_h + 70), "white")
d = ImageDraw.Draw(sheet)
d.text((10, 10), "OakInk split000 — automatic internal selector LLM comparison", fill=(0, 0, 0))
d.text((10, 35), "Red frame = selected object candidate sent into joint alignment", fill=(180, 0, 0))

for r, row in enumerate(rows):
    for c, im in enumerate(row):
        sheet.paste(im, (c * cell_w, 70 + r * cell_h))

out = HOME / "foho_phase0/inspection/oakink_000/oakink000_auto_selector_llm_grid_v3.jpg"
sheet.save(out, quality=95)
print("[OK] wrote", out)
