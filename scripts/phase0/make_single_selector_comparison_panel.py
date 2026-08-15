from pathlib import Path
from PIL import Image, ImageDraw
import argparse
import re
import trimesh
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def find_first(root, patterns):
    root = Path(root)
    for pat in patterns:
        hits = sorted(root.glob(pat))
        if hits:
            return hits[0]
    return None


def load_mesh(path):
    if path is None or not Path(path).exists():
        return None
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh


def largest_component(mesh):
    comps = mesh.split(only_watertight=False)
    if not comps:
        return mesh
    return max(comps, key=lambda m: len(m.faces))


def robust_points(mesh, n=12000):
    pts = np.asarray(mesh.vertices)
    if len(pts) > n:
        rng = np.random.default_rng(0)
        pts = pts[rng.choice(len(pts), n, replace=False)]
    return pts


def normalize_mesh_for_object_view(mesh):
    """
    Normalize object-only candidates for visual comparison.
    This is NOT for metric evaluation. It is only for readable panels.
    """
    mesh = mesh.copy()
    pts = np.asarray(mesh.vertices)
    center = pts.mean(axis=0)
    scale = np.max(np.linalg.norm(pts - center, axis=1))
    scale = max(float(scale), 1e-6)
    mesh.vertices = (mesh.vertices - center) / scale
    return mesh


def render_meshes(mesh_paths, out_png, title="", colors=None, normalize_object=False, largest_only=False):
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)

    if colors is None:
        colors = ["0.25", "green"]

    meshes = []
    for p in mesh_paths:
        mesh = load_mesh(p)
        if mesh is None or len(mesh.vertices) == 0:
            continue
        if largest_only:
            mesh = largest_component(mesh)
        if normalize_object:
            mesh = normalize_mesh_for_object_view(mesh)
        meshes.append(mesh)

    fig = plt.figure(figsize=(4.2, 3.2))
    ax = fig.add_subplot(111, projection="3d")

    all_pts = []
    for idx, mesh in enumerate(meshes):
        pts = robust_points(mesh)
        all_pts.append(pts)

        # point rendering is more stable than face rendering on broken meshes
        ax.scatter(
            pts[:, 0], pts[:, 1], pts[:, 2],
            s=0.45,
            c=colors[min(idx, len(colors) - 1)],
            alpha=0.85,
        )

    if all_pts:
        pts = np.concatenate(all_pts, axis=0)

        # robust crop to avoid tiny far-away fragments ruining the view
        lo = np.percentile(pts, 2, axis=0)
        hi = np.percentile(pts, 98, axis=0)
        center = (lo + hi) / 2
        radius = float(np.max(hi - lo) / 2)
        radius = max(radius * 1.25, 1e-6)

        ax.set_xlim(center[0] - radius, center[0] + radius)
        ax.set_ylim(center[1] - radius, center[1] + radius)
        ax.set_zlim(center[2] - radius, center[2] + radius)

    ax.view_init(elev=18, azim=-70)
    ax.set_axis_off()
    ax.set_title(title, fontsize=9)
    plt.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def load_img(path, size=(360, 280), label=""):
    canvas = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(canvas)

    if path is None or not Path(path).exists():
        draw.text((115, 130), "MISSING", fill=(180, 0, 0))
    else:
        img = Image.open(path).convert("RGB")
        img.thumbnail((size[0] - 20, size[1] - 55))
        x = (size[0] - img.width) // 2
        y = 45
        canvas.paste(img, (x, y))

    draw.text((8, 8), label, fill=(0, 0, 0))
    return canvas


def parse_selector_decision(log_path):
    text = Path(log_path).read_text(errors="ignore") if Path(log_path).exists() else ""
    m = re.findall(
        r"before_frag=([0-9.]+), current_frag=([0-9.]+), margin=([0-9.]+), selected=([A-Za-z0-9_]+)",
        text,
    )
    if not m:
        return "before=?\nafter=?\nselected=missing", None

    before, current, margin, selected = m[-1]
    return f"before={before}\nafter={current}\nselected={selected}", selected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run_id", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    home = Path.home()
    run = home / "foho_phase0/runs" / args.run_id
    debug = home / "foho_phase0/inspection/oakink_000" / args.run_id / "internal_selector_debug"
    log = home / "foho_phase0/logs" / f"{args.run_id}.log"

    tmp = home / "foho_phase0/inspection/oakink_000" / args.run_id / "single_panel_tmp_v2"
    tmp.mkdir(parents=True, exist_ok=True)

    crop = find_first(run, ["cropped_hoi_imgs/*cropped*hoi*.png", "cropped_hoi_imgs/*.png"])
    inpaint = find_first(run, ["ours_inpaint/*inpaint*.png", "**/*inpainted*object*.png", "**/*inpaint*.png"])

    before = debug / "selector_candidate_before_phase42.ply"
    after = debug / "selector_candidate_phase42_before_joint_true.ply"
    if not after.exists():
        after = debug / "selector_candidate_phase42_before_joint.ply"
    selected = debug / "selector_selected_before_joint.ply"

    final_obj = find_first(run, ["guidance_out/*obj*.ply", "guidance_out/test_obj.ply"])
    final_hand = find_first(run, ["guidance_out/*hand*.ply", "guidance_out/test_hand.ply"])

    before_png = tmp / "before_phase42_normalized.png"
    after_png = tmp / "after_phase42_normalized.png"
    selected_png = tmp / "selected_normalized.png"
    final_png = tmp / "final_scene_native.png"

    decision_text, selected_name = parse_selector_decision(log)

    render_meshes([before], before_png, "object before 4.2\nnormalized view", normalize_object=True)
    render_meshes([after], after_png, "object after 4.2\nnormalized view", normalize_object=True)
    render_meshes([selected], selected_png, "selected object\nnormalized view", normalize_object=True)
    render_meshes([final_obj, final_hand], final_png, "final scene\nnative final frame", colors=["0.25", "green"], normalize_object=False)

    cells = [
        load_img(crop, label=f"{args.label}\n1 crop"),
        load_img(inpaint, label="2 inpaint"),
        load_img(before_png, label="3 before Phase 4.2"),
        load_img(after_png, label="4 after Phase 4.2"),
        load_img(selected_png, label=f"5 selector choice\n{decision_text}"),
        load_img(final_png, label="6 final scene"),
    ]

    if selected_name == "before_phase42":
        ImageDraw.Draw(cells[2]).rectangle([3, 3, cells[2].width - 4, cells[2].height - 4], outline=(255, 0, 0), width=6)
    elif selected_name == "phase42_before_joint":
        ImageDraw.Draw(cells[3]).rectangle([3, 3, cells[3].width - 4, cells[3].height - 4], outline=(255, 0, 0), width=6)

    w = cells[0].width * len(cells)
    h = cells[0].height + 36
    panel = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(panel)
    draw.text(
        (8, h - 28),
        "Note: object-candidate columns are normalized for shape/fragmentation comparison; final scene uses native final hand-object frame.",
        fill=(160, 0, 0),
    )

    for i, cell in enumerate(cells):
        panel.paste(cell, (i * cell.width, 0))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    panel.save(out)
    print("[OK] wrote", out)


if __name__ == "__main__":
    main()
