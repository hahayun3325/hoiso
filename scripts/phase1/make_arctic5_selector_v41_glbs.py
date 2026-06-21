#!/usr/bin/env python
from pathlib import Path
import pandas as pd
import trimesh

PANEL_OUT = Path("/home/fredcui/foho_phase0/phase1_diagnostics/arctic5_selector_v41_panels")
MANIFEST = PANEL_OUT / "arctic5_selector_v41_panel_manifest.csv"
GLB_DIR = PANEL_OUT / "visual_glbs"
GLB_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(MANIFEST)

for _, r in df.iterrows():
    if not bool(r["hand_mesh"]) or not bool(r["object_mesh"]):
        continue

    hand_path = Path(str(r["hand_mesh"]))
    obj_path = Path(str(r["object_mesh"]))

    if not hand_path.exists() or not obj_path.exists():
        print("[MISS]", r["case"], r["method"])
        continue

    hand = trimesh.load(hand_path, force="mesh")
    obj = trimesh.load(obj_path, force="mesh")

    hand.visual.vertex_colors = [230, 180, 140, 255]
    obj.visual.vertex_colors = [90, 150, 240, 255]

    scene = trimesh.Scene()
    scene.add_geometry(hand, node_name="hand")
    scene.add_geometry(obj, node_name="object")

    method = str(r["method"])
    out = GLB_DIR / f"{r['case']}__{method}.glb"
    scene.export(out)
    print("[OK]", out)
