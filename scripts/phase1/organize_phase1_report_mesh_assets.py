#!/usr/bin/env python
from pathlib import Path
import shutil
import pandas as pd
import trimesh

REPORT_OUT = Path("/home/fredcui/foho_phase0/phase1_report_assets")
MANIFEST = REPORT_OUT / "manifests/report_asset_manifest.csv"

df = pd.read_csv(MANIFEST)

rows = []

for _, r in df.iterrows():
    case = r["case"]
    method = r["method_key"]

    out_dir = REPORT_OUT / "meshes" / case / method
    out_dir.mkdir(parents=True, exist_ok=True)

    hand_src = Path(str(r["hand_mesh"]))
    obj_src = Path(str(r["object_mesh"]))

    status = "ok"

    if not hand_src.exists() or not obj_src.exists():
        status = "missing_mesh"
        rows.append({
            **r.to_dict(),
            "status": status,
            "copied_hand": "",
            "copied_object": "",
            "combined_ply": "",
            "combined_glb": "",
        })
        continue

    hand_dst = out_dir / "final_hand.ply"
    obj_dst = out_dir / "final_object.ply"
    combined_ply = out_dir / "final_hoi_colored.ply"
    combined_glb = out_dir / "final_hoi_scene.glb"

    shutil.copy2(hand_src, hand_dst)
    shutil.copy2(obj_src, obj_dst)

    hand = trimesh.load(hand_dst, force="mesh")
    obj = trimesh.load(obj_dst, force="mesh")

    hand.visual.vertex_colors = [230, 180, 140, 255]
    obj.visual.vertex_colors = [80, 140, 240, 255]

    combined = trimesh.util.concatenate([hand, obj])
    combined.export(combined_ply)

    scene = trimesh.Scene()
    scene.add_geometry(hand, node_name="hand")
    scene.add_geometry(obj, node_name="object")
    scene.export(combined_glb)

    rows.append({
        **r.to_dict(),
        "status": status,
        "copied_hand": str(hand_dst),
        "copied_object": str(obj_dst),
        "combined_ply": str(combined_ply),
        "combined_glb": str(combined_glb),
    })

out = pd.DataFrame(rows)
out_path = REPORT_OUT / "manifests/report_mesh_asset_manifest.csv"
out.to_csv(out_path, index=False)

print("[OK] wrote", out_path)
print(out[["case", "method_key", "status", "combined_ply", "combined_glb"]].to_string(index=False))
