#!/usr/bin/env python
from pathlib import Path
import numpy as np
import pandas as pd
import trimesh
from scipy.spatial import cKDTree


def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh


def color(mesh, rgba):
    mesh = mesh.copy()
    mesh.visual.vertex_colors = np.tile(np.array(rgba, dtype=np.uint8), (len(mesh.vertices), 1))
    return mesh


def sample_obj(mesh, n=30000):
    if hasattr(mesh, "faces") and len(mesh.faces) > 0:
        try:
            pts, _ = trimesh.sample.sample_surface(mesh, n)
            return pts
        except Exception:
            pass
    return np.asarray(mesh.vertices)


def spheres(points, radius=0.006, max_n=300):
    if len(points) == 0:
        return None
    if len(points) > max_n:
        idx = np.linspace(0, len(points) - 1, max_n).astype(int)
        points = points[idx]

    parts = []
    for p in points:
        s = trimesh.creation.uv_sphere(radius=radius, count=[12, 12])
        s.apply_translation(p)
        s.visual.vertex_colors = np.tile(np.array([[255, 0, 0, 255]], dtype=np.uint8), (len(s.vertices), 1))
        parts.append(s)
    return trimesh.util.concatenate(parts)


phase1 = Path("/home/fredcui/foho_phase0/phase1_diagnostics")
io_dir = phase1 / "io_alignment"
out_dir = phase1 / "visual_inspection_step2_combined_v2"
out_dir.mkdir(parents=True, exist_ok=True)

priority = pd.read_csv(phase1 / "first_contact_metrics/contact_metrics_summary_labeled.csv")
pen = pd.read_csv(phase1 / "penetration_diagnostics/penetration_diagnostics_summary.csv")

df = priority.merge(
    pen[["sample_id", "object_inside_hand_ratio", "hand_inside_object_ratio"]],
    on="sample_id",
    how="left"
)

df = df[
    (df["floating"] == True)
    | (df["contact_status_label"] == "heavy_contact_check_penetration")
    | (df["object_inside_hand_ratio"].fillna(0) > 0.02)
    | (df["hand_inside_object_ratio"].fillna(0) > 0.10)
].copy()

rows = []

for _, r in df.iterrows():
    sid = r["sample_id"]
    dst = out_dir / sid
    dst.mkdir(parents=True, exist_ok=True)

    hand = load_mesh(io_dir / sid / "pred_hand_aligned.ply")
    obj = load_mesh(io_dir / sid / "pred_object_aligned.ply")

    hand_c = color(hand, [255, 190, 40, 255])
    obj_c = color(obj, [70, 120, 255, 180])

    hv = np.asarray(hand.vertices)
    op = sample_obj(obj)
    d, _ = cKDTree(op).query(hv, k=1)
    near = hv[d < 0.005]
    marker_mesh = spheres(near)

    scene = trimesh.Scene()
    scene.add_geometry(hand_c, node_name="hand_orange")
    scene.add_geometry(obj_c, node_name="object_blue")
    if marker_mesh is not None:
        scene.add_geometry(marker_mesh, node_name="near_contact_red_markers")

    scene.export(dst / "hand_object_contact_scene.glb")
    hand_c.export(dst / "hand_orange.ply")
    obj_c.export(dst / "object_blue.ply")
    if marker_mesh is not None:
        marker_mesh.export(dst / "near_contact_red_markers.ply")

    rows.append({
        "sample_id": sid,
        "scene_glb": str(dst / "hand_object_contact_scene.glb"),
        "near_contact_markers": len(near),
        "floating": r["floating"],
        "contact_status_label": r["contact_status_label"],
        "object_inside_hand_ratio": r.get("object_inside_hand_ratio", ""),
        "hand_inside_object_ratio": r.get("hand_inside_object_ratio", ""),
    })

out = out_dir / "visual_scene_v2_manifest.csv"
pd.DataFrame(rows).to_csv(out, index=False)
print("[OK] wrote", out)
print(pd.DataFrame(rows).to_string(index=False))
