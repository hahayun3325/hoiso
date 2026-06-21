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

PANEL_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_comparison_panels_fixed")
MANIFEST = PANEL_OUT / "selector_v41_panel_manifest_fixed.csv"
SNAP_DIR = PANEL_OUT / "snapshots"
PANEL_DIR = PANEL_OUT / "case_panels"

SNAP_DIR.mkdir(parents=True, exist_ok=True)
PANEL_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(MANIFEST).fillna("")

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

    fig = plt.figure(figsize=(4.2, 3.6), dpi=150)
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
        ax.text2D(0.35, 0.5, "MISSING MESH", transform=ax.transAxes)

    ax.set_axis_off()
    plt.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

def image_cell(path, title, size=(360, 300)):
    cell = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(cell)
    draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=(180, 180, 180))
    draw.text((8, 8), title, fill=(0, 0, 0), font=font)

    p = Path(str(path))
    if p.exists():
        im = Image.open(p).convert("RGB")
        im.thumbnail((size[0] - 20, size[1] - 42))
        x = (size[0] - im.width) // 2
        y = 36 + (size[1] - 42 - im.height) // 2
        cell.paste(im, (x, y))
    else:
        draw.text((20, 140), "MISSING IMAGE", fill=(180, 0, 0), font=font)
    return cell

def text_cell(title, text, size=(360, 300)):
    cell = Image.new("RGB", size, (255, 255, 255))
    draw = ImageDraw.Draw(cell)
    draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=(180, 180, 180))
    draw.text((8, 8), title, fill=(0, 0, 0), font=font)
    y = 40
    for line in textwrap.wrap(str(text), width=42):
        draw.text((10, y), line, fill=(40, 40, 40), font=font_small)
        y += 16
    return cell

panel_paths = []

for _, r in df.iterrows():
    case = r["case"]

    b_snap = SNAP_DIR / f"{case}_baseline.png"
    o_snap = SNAP_DIR / f"{case}_old_gpt55.png"
    v_snap = SNAP_DIR / f"{case}_selector_v41.png"

    render_pair(r["baseline_hand"], r["baseline_object"], b_snap, "baseline")
    render_pair(r["old_gpt55_hand"], r["old_gpt55_object"], o_snap, "old GPT-5.5 selector")
    render_pair(r["selector_v41_hand"], r["selector_v41_object"], v_snap, "selector-v4.1 selected")

    decision_text = (
        f"chosen_method: {r['selector_v41_chosen_method']}\n"
        f"next_stage: {r['selector_v41_next_stage']}\n"
        f"warning_tags: {r['selector_v41_warning_tags']}\n"
        f"decision_json: {r['selector_v41_decision_json']}"
    )

    cells = [
        image_cell(r["input_image"], f"{case}: input"),
        image_cell(b_snap, "baseline"),
        image_cell(o_snap, "selector + GPT-5.5"),
        image_cell(v_snap, "selector-v4.1"),
        text_cell("selector-v4.1 decision", decision_text),
    ]

    W = sum(c.width for c in cells)
    H = max(c.height for c in cells) + 40
    panel = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(panel)
    draw.text((10, 8), f"{case}: baseline vs GPT-5.5 selector vs selector-v4.1", fill=(0, 0, 0), font=font_title)

    x = 0
    for c in cells:
        panel.paste(c, (x, 40))
        x += c.width

    out = PANEL_DIR / f"{case}_selector_v41_fixed_panel.jpg"
    panel.save(out)
    panel_paths.append(out)
    print("[OK] wrote", out)

# Contact sheet.
if panel_paths:
    imgs = [Image.open(p).convert("RGB") for p in panel_paths]
    W = max(im.width for im in imgs)
    H = sum(im.height for im in imgs)
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    y = 0
    for im in imgs:
        sheet.paste(im, (0, y))
        y += im.height
    out = PANEL_OUT / "selector_v41_all_cases_fixed_sheet.jpg"
    sheet.save(out)
    print("[OK] wrote", out)
