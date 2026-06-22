#!/usr/bin/env python
from pathlib import Path
import textwrap
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import trimesh

PERF_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_performance")
PANEL_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/panels")
SNAP_DIR = PANEL_OUT / "snapshots"
CASE_DIR = PANEL_OUT / "case_panels"

MANIFEST = PERF_OUT / "arctic5_selector_performance_manifest.csv"
COMBINED = PERF_OUT / "arctic5_selector_combined_performance.csv"
REL = PERF_OUT / "arctic5_relative_pose_metrics.csv"

SNAP_DIR.mkdir(parents=True, exist_ok=True)
CASE_DIR.mkdir(parents=True, exist_ok=True)

manifest = pd.read_csv(MANIFEST).fillna("")
combined = pd.read_csv(COMBINED).fillna("")
rel = pd.read_csv(REL).fillna("")

df = manifest.merge(
    combined[["case", "method", "run_id", "object_cd_mm", "object_f10", "contact_p5_mm", "selector_v4_gate"]],
    on=["case", "method", "run_id"],
    how="left",
)

df = df.merge(
    rel[["case", "method", "run_id", "relative_object_center_error_mm"]],
    on=["case", "method", "run_id"],
    how="left",
)

try:
    font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    font = ImageFont.truetype("DejaVuSans.ttf", 15)
    font_small = ImageFont.truetype("DejaVuSans.ttf", 12)
except Exception:
    font_title = font = font_small = None

def load_vertices(path, max_points=7000):
    path = Path(str(path))
    if not path.exists():
        return None
    geom = trimesh.load(path, process=False)
    if isinstance(geom, trimesh.Scene):
        geom = trimesh.util.concatenate(tuple(geom.geometry.values()))
    v = np.asarray(geom.vertices, dtype=np.float64)
    if len(v) > max_points:
        idx = np.linspace(0, len(v) - 1, max_points).astype(int)
        v = v[idx]
    return v

def render_pair(hand_path, obj_path, out_path, title):
    hand = load_vertices(hand_path)
    obj = load_vertices(obj_path)

    fig = plt.figure(figsize=(4.0, 3.4), dpi=150)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_title(title, fontsize=9)

    all_v = []
    if obj is not None:
        ax.scatter(obj[:, 0], obj[:, 1], obj[:, 2], s=0.35, alpha=0.85, c="tab:blue")
        all_v.append(obj)
    if hand is not None:
        ax.scatter(hand[:, 0], hand[:, 1], hand[:, 2], s=0.35, alpha=0.85, c="tab:orange")
        all_v.append(hand)

    if all_v:
        v = np.concatenate(all_v, axis=0)
        lo, hi = v.min(axis=0), v.max(axis=0)
        center = (lo + hi) / 2
        radius = max((hi - lo).max() / 2, 1e-6)
        ax.set_xlim(center[0] - radius, center[0] + radius)
        ax.set_ylim(center[1] - radius, center[1] + radius)
        ax.set_zlim(center[2] - radius, center[2] + radius)
        ax.view_init(elev=20, azim=-60)
    else:
        ax.text2D(0.30, 0.5, "MISSING MESH", transform=ax.transAxes)

    ax.set_axis_off()
    plt.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

def image_cell(path, title, caption, size=(360, 330)):
    cell = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(cell)
    draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=(180, 180, 180))
    draw.text((8, 8), title, fill=(0, 0, 0), font=font)

    p = Path(str(path))
    if p.exists():
        im = Image.open(p).convert("RGB")
        im.thumbnail((size[0] - 20, 210))
        x = (size[0] - im.width) // 2
        y = 34 + (210 - im.height) // 2
        cell.paste(im, (x, y))
    else:
        draw.text((20, 130), "MISSING IMAGE", fill=(180, 0, 0), font=font)

    y = 250
    for line in textwrap.wrap(str(caption), width=44)[:4]:
        draw.text((8, y), line, fill=(40, 40, 40), font=font_small)
        y += 16
    return cell

def fmt(x, nd=1):
    try:
        if pd.isna(x):
            return "nan"
        return f"{float(x):.{nd}f}"
    except Exception:
        return "nan"

method_order = [
    ("default_baseline", "baseline"),
    ("old_gpt55_selector_v1", "selector + GPT-5.5"),
    ("partaware_v2_attempt0", "part-aware attempt0"),
    ("selector_v41_refined_pipeline", "selector-v4.1 pipeline"),
]

panel_paths = []

for case, sub in df.groupby("case"):
    input_image = sub.iloc[0]["input_image"]

    cells = []
    cells.append(image_cell(input_image, f"{case}: input", "cropped input"))

    for method, label in method_order:
        row = sub[sub["method"] == method]
        if row.empty:
            snap = ""
            caption = "missing method"
        else:
            r = row.iloc[0]
            snap = SNAP_DIR / f"{case}_{method}.png"
            render_pair(r["hand_mesh"], r["object_mesh"], snap, label)
            caption = (
                f"CD {fmt(r.get('object_cd_mm'))} | F10 {fmt(r.get('object_f10'), 3)} | "
                f"p5 {fmt(r.get('contact_p5_mm'))} | rel {fmt(r.get('relative_object_center_error_mm'))} | "
                f"{r.get('selector_v4_gate', '')}"
            )

        cells.append(image_cell(snap, label, caption))

    W = sum(c.width for c in cells)
    H = max(c.height for c in cells) + 42

    panel = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(panel)
    draw.text((10, 8), f"{case}: full-pipeline comparison", fill=(0, 0, 0), font=font_title)

    x = 0
    for c in cells:
        panel.paste(c, (x, 42))
        x += c.width

    out = CASE_DIR / f"{case}_selector_v41_full_pipeline_panel.jpg"
    panel.save(out)
    panel_paths.append(out)
    print("[OK] wrote", out)

# Contact sheet
if panel_paths:
    imgs = [Image.open(p).convert("RGB") for p in panel_paths]
    W = max(im.width for im in imgs)
    H = sum(im.height for im in imgs)
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    y = 0
    for im in imgs:
        sheet.paste(im, (0, y))
        y += im.height
    out = PANEL_OUT / "selector_v41_full_pipeline_all_cases_sheet.jpg"
    sheet.save(out)
    print("[OK] wrote", out)
