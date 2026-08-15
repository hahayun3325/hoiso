#!/usr/bin/env python
from pathlib import Path
import pandas as pd
import trimesh

MANIFEST = Path("docs/phase1/step3_prompt_refined_rerun/aket01_attempt0/aket01_visual_mesh_manifest.csv")
OUT_DIR = Path("docs/phase1/step3_prompt_refined_rerun/aket01_attempt0/visual_glbs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(MANIFEST)

for _, r in df.iterrows():
    label = str(r["label"])
    hand_path = str(r.get("hand_mesh", "") or "")
    obj_path = str(r.get("object_mesh", "") or "")

    if not hand_path or not obj_path or hand_path == "nan" or obj_path == "nan":
        continue

    hand = trimesh.load(hand_path, force="mesh")
    obj = trimesh.load(obj_path, force="mesh")

    hand.visual.vertex_colors = [220, 160, 120, 255]
    obj.visual.vertex_colors = [80, 140, 240, 255]

    scene = trimesh.Scene()
    scene.add_geometry(hand, node_name=f"{label}_hand")
    scene.add_geometry(obj, node_name=f"{label}_object")

    out = OUT_DIR / f"{label}.glb"
    scene.export(out)
    print("[OK] wrote", out)
