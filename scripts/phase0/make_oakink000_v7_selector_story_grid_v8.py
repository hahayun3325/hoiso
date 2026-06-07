from pathlib import Path
from PIL import Image, ImageDraw
import hashlib
import re
import csv
import textwrap
import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HOME = Path.home()
ROOT = Path("/home/fredcui/Projects/FollowMyHold")

RUNS = [
    ("oakink000_gemini31pro_short", "Gemini-3.1-pro"),
    ("oakink000_sonnet46thinking_short", "Sonnet-4.6-thinking"),
    ("oakink000_gpt55_short", "GPT-5.5"),
    ("oakink000_gpt55thinking_short", "GPT-5.5-thinking"),
]

SUFFIX = "selector_auto_frag_v7_truefile"
OUT_DIR = HOME / "foho_phase0/inspection/oakink_000/v7_selector_story_grid_v8"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PROMPT_CSVS = [
    ROOT / "docs/phase0/manual_llm_prompts/oakink000_prompt_candidates_short.csv",
    ROOT / "docs/phase0/manual_llm_prompts/oakink000_prompt_candidates.csv",
]


def first_existing(paths):
    for p in paths:
        p = Path(p)
        if p.exists():
            return p
    return None


def first_glob(base, patterns):
    base = Path(base)
    for pat in patterns:
        hits = sorted(base.glob(pat))
        if hits:
            return hits[0]
    return None


def load_prompt_map():
    out = {}
    for csv_path in PROMPT_CSVS:
        if not csv_path.exists():
            continue
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                llm = (row.get("llm") or row.get("model") or "").strip()
                run_id = (row.get("run_id") or "").strip()
                prompt = (
                    row.get("prompt")
                    or row.get("manual_prompt")
                    or row.get("object_prompt")
                    or row.get("response")
                    or ""
                ).strip()
                if prompt:
                    if llm:
                        out[llm.lower()] = prompt
                    if run_id:
                        out[run_id] = prompt
    return out


PROMPTS = load_prompt_map()


def md5(path):
    path = Path(path)
    if not path.exists():
        return ""
    return hashlib.md5(path.read_bytes()).hexdigest()


def parse_selector_decision(run_id):
    log = HOME / "foho_phase0/logs" / f"{run_id}.log"
    text = log.read_text(errors="ignore") if log.exists() else ""

    matches = re.findall(
        r"before_frag=([0-9.]+), current_frag=([0-9.]+), margin=([0-9.]+), selected=([A-Za-z0-9_]+)",
        text,
    )

    if not matches:
        return {
            "before": "?",
            "after": "?",
            "selected": "missing",
            "status": "missing selector line",
        }

    before, after, margin, selected = matches[-1]
    return {
        "before": before,
        "after": after,
        "selected": selected,
        "status": "OK",
    }


def load_mesh(path):
    if path is None or not Path(path).exists():
        return None
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
        return None
    return mesh


def normalize_mesh(mesh):
    mesh = mesh.copy()
    pts = np.asarray(mesh.vertices)
    center = (pts.min(axis=0) + pts.max(axis=0)) / 2.0
    span = float(np.max(pts.max(axis=0) - pts.min(axis=0)))
    span = max(span, 1e-8)
    mesh.vertices = (mesh.vertices - center) / span
    return mesh


def downsample_faces(mesh, max_faces=9000):
    if len(mesh.faces) <= max_faces:
        return mesh
    rng = np.random.default_rng(0)
    keep = rng.choice(len(mesh.faces), size=max_faces, replace=False)
    faces = mesh.faces[keep]
    used = np.unique(faces.reshape(-1))
    remap = {old: i for i, old in enumerate(used)}
    new_vertices = mesh.vertices[used]
    new_faces = np.vectorize(remap.get)(faces)
    return trimesh.Trimesh(vertices=new_vertices, faces=new_faces, process=False)


def add_mesh_surface(ax, mesh, face_color="0.25", alpha=1.0):
    mesh = downsample_faces(mesh)
    verts = np.asarray(mesh.vertices)
    faces = np.asarray(mesh.faces)

    tris = verts[faces]
    poly = Poly3DCollection(
        tris,
        facecolors=face_color,
        edgecolors="none",
        linewidths=0.0,
        alpha=alpha,
    )
    ax.add_collection3d(poly)


def set_equal_axes(ax, meshes):
    pts = []
    for m in meshes:
        if m is not None:
            pts.append(np.asarray(m.vertices))
    if not pts:
        return
    pts = np.concatenate(pts, axis=0)
    mn = pts.min(axis=0)
    mx = pts.max(axis=0)
    center = (mn + mx) / 2.0
    span = float(np.max(mx - mn))
    span = max(span, 1e-6)
    ax.set_xlim(center[0] - span / 2, center[0] + span / 2)
    ax.set_ylim(center[1] - span / 2, center[1] + span / 2)
    ax.set_zlim(center[2] - span / 2, center[2] + span / 2)


def render_meshes(mesh_paths, out_png, title="", colors=None, normalize=True, view="object"):
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)

    if colors is None:
        colors = ["0.25", "green"]

    meshes = []
    for p in mesh_paths:
        mesh = load_mesh(p)
        if mesh is not None:
            if normalize:
                mesh = normalize_mesh(mesh)
            meshes.append(mesh)
        else:
            meshes.append(None)

    fig = plt.figure(figsize=(4.2, 3.7))
    ax = fig.add_subplot(111, projection="3d")

    valid = [m for m in meshes if m is not None]
    if not valid:
        ax.text2D(0.36, 0.5, "MISSING", transform=ax.transAxes, color="red", fontsize=14)
    else:
        for idx, mesh in enumerate(meshes):
            if mesh is None:
                continue
            add_mesh_surface(ax, mesh, face_color=colors[idx % len(colors)], alpha=0.95)
        set_equal_axes(ax, valid)

    if view == "object":
        ax.view_init(elev=18, azim=-70)
    elif view == "final":
        ax.view_init(elev=22, azim=-55)
    else:
        ax.view_init(elev=18, azim=-70)

    ax.set_title(title, fontsize=9)
    ax.set_axis_off()
    plt.tight_layout()
    fig.savefig(out_png, dpi=170)
    plt.close(fig)


def image_card(path, title, subtitle="", size=(420, 330), border=False):
    w, h = size
    card = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(card)
    d.text((10, 8), title, fill=(0, 0, 0))
    if subtitle:
        for i, line in enumerate(textwrap.wrap(subtitle, width=48)[:4]):
            d.text((10, 28 + i * 16), line, fill=(80, 80, 80))

    y0 = 92
    if path and Path(path).exists():
        im = Image.open(path).convert("RGB")
        im.thumbnail((w - 24, h - y0 - 12))
        card.paste(im, ((w - im.width) // 2, y0))
    else:
        d.text((w // 2 - 40, h // 2), "MISSING", fill=(200, 0, 0))

    if border:
        for k in range(6):
            d.rectangle((k, k, w - 1 - k, h - 1 - k), outline=(255, 0, 0))
    return card


def get_prompt(base_id, label):
    return PROMPTS.get(base_id) or PROMPTS.get(label.lower()) or ""


rows = []
for base_id, label in RUNS:
    run_id = f"{base_id}_{SUFFIX}"
    run = HOME / "foho_phase0/runs" / run_id
    debug = HOME / "foho_phase0/inspection/oakink_000" / run_id / "internal_selector_debug"

    crop = first_glob(run, [
        "cropped_hoi_imgs/*cropped*hoi*.png",
        "cropped_hoi_imgs/*.png",
    ]) or first_existing([
        HOME / "foho_phase0/runs/oakink_000_baseline/cropped_hoi_imgs/oakink_cropped_hoi_1.png",
    ])

    inpaint = first_glob(run, [
        "ours_inpaint/*inpainted*object*.png",
        "ours_inpaint/*inpaint*.png",
        "ours_inpaint/*.png",
    ])

    before = debug / "selector_candidate_before_phase42.ply"
    after = debug / "selector_candidate_phase42_before_joint_true.ply"
    selected = debug / "selector_selected_before_joint.ply"

    final_obj = first_existing([
        run / "guidance_out/oakink_obj.ply",
        run / "guidance_out/test_obj.ply",
    ])
    final_hand = first_existing([
        run / "guidance_out/oakink_hand.ply",
        run / "guidance_out/test_hand.ply",
    ])

    decision = parse_selector_decision(run_id)

    before_png = OUT_DIR / f"{run_id}_before_surface.png"
    after_png = OUT_DIR / f"{run_id}_after_surface.png"
    selected_png = OUT_DIR / f"{run_id}_selected_surface.png"
    final_png = OUT_DIR / f"{run_id}_final_surface.png"

    render_meshes([before], before_png, "before Phase 4.2", ["0.25"], normalize=True, view="object")
    render_meshes([after], after_png, "after Phase 4.2", ["0.25"], normalize=True, view="object")
    render_meshes([selected], selected_png, "selected before joint", ["0.25"], normalize=True, view="object")

    # Final scene is normalized as a whole scene, keeping hand-object relationship.
    render_meshes([final_obj, final_hand], final_png, "final object + hand", ["0.25", "green"], normalize=True, view="final")

    prompt = get_prompt(base_id, label)
    prompt_short = prompt[:140] + ("..." if len(prompt) > 140 else "")

    before_hash = md5(before)
    after_hash = md5(after)
    selected_hash = md5(selected)

    rows.append({
        "label": label,
        "crop": crop,
        "inpaint": inpaint,
        "before_png": before_png,
        "after_png": after_png,
        "selected_png": selected_png,
        "final_png": final_png,
        "decision": decision,
        "prompt": prompt_short,
        "before_border": decision["selected"] == "before_phase42",
        "after_border": decision["selected"] == "phase42_before_joint",
        "selected_hash_ok": selected_hash in {before_hash, after_hash} and selected_hash != "",
    })


card_w, card_h = 420, 330
cols = [
    "crop",
    "inpaint",
    "before Phase 4.2",
    "after Phase 4.2",
    "selected before joint",
    "final scene",
]

header_h = 80
sheet = Image.new("RGB", (card_w * len(cols), header_h + card_h * len(rows)), "white")
draw = ImageDraw.Draw(sheet)

draw.text((10, 8), "OakInk split000 V7 automatic internal selector — readable surface rendering", fill=(0, 0, 0))
draw.text((10, 34), "Red frame = selected object candidate. Candidate meshes use object-local view; final scene uses final-scene local view.", fill=(140, 0, 0))

for i, col in enumerate(cols):
    draw.text((i * card_w + 10, 58), col, fill=(0, 0, 0))

for r, item in enumerate(rows):
    y = header_h + r * card_h
    dec = item["decision"]
    label = item["label"]

    decision_text = f"before={dec['before']} after={dec['after']} selected={dec['selected']}"
    hash_text = "md5 selected OK" if item["selected_hash_ok"] else "md5 check needed"

    cards = [
        image_card(item["crop"], f"{label}: crop", "cropped HOI input", (card_w, card_h)),
        image_card(item["inpaint"], f"{label}: inpaint", item["prompt"] or "LLM prompt + FLUX", (card_w, card_h)),
        image_card(item["before_png"], f"{label}: before 4.2", decision_text, (card_w, card_h), border=item["before_border"]),
        image_card(item["after_png"], f"{label}: after 4.2", decision_text, (card_w, card_h), border=item["after_border"]),
        image_card(item["selected_png"], f"{label}: selector output", hash_text, (card_w, card_h), border=True),
        image_card(item["final_png"], f"{label}: final scene", "final hand-object frame, normalized for view", (card_w, card_h)),
    ]

    for c, card in enumerate(cards):
        sheet.paste(card, (c * card_w, y))

out = HOME / "foho_phase0/inspection/oakink_000/oakink000_v7_selector_story_grid_v8_surface.jpg"
sheet.save(out, quality=95)
print("[OK] wrote", out)
