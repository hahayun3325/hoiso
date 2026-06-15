#!/usr/bin/env python
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import trimesh
from scipy.spatial import cKDTree


def load_geom(path):
    geom = trimesh.load(path, process=False)
    if isinstance(geom, trimesh.Scene):
        geom = trimesh.util.concatenate(tuple(geom.geometry.values()))
    return geom


def color_geom(geom, rgba):
    geom = geom.copy()
    rgba = np.asarray(rgba, dtype=np.uint8)

    if hasattr(geom, "vertices"):
        colors = np.tile(rgba[None, :], (len(geom.vertices), 1))
        geom.visual.vertex_colors = colors

    return geom


def object_points(obj, n=30000):
    if hasattr(obj, "faces") and len(obj.faces) > 0:
        try:
            pts, _ = trimesh.sample.sample_surface(obj, n)
            return np.asarray(pts)
        except Exception:
            pass
    return np.asarray(obj.vertices)


def make_spheres(points, radius=0.003, max_markers=200):
    points = np.asarray(points)
    if len(points) == 0:
        return None

    # Keep the scene readable.
    if len(points) > max_markers:
        idx = np.linspace(0, len(points) - 1, max_markers).astype(int)
        points = points[idx]

    parts = []
    for p in points:
        s = trimesh.creation.uv_sphere(radius=radius, count=[8, 8])
        s.apply_translation(p)
        s.visual.vertex_colors = np.tile(
            np.array([[255, 30, 30, 255]], dtype=np.uint8),
            (len(s.vertices), 1)
        )
        parts.append(s)

    return trimesh.util.concatenate(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase1-out", default="/home/fredcui/foho_phase0/phase1_diagnostics")
    parser.add_argument("--priority-csv", default=None)
    parser.add_argument("--contact-mm", type=float, default=5.0)
    args = parser.parse_args()

    phase1 = Path(args.phase1_out)
    io_dir = phase1 / "io_alignment"
    out_dir = phase1 / "visual_inspection_step2_combined"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.priority_csv is None:
        priority_csv = phase1 / "first_contact_metrics/visual_inspection_priority.csv"
    else:
        priority_csv = Path(args.priority_csv)

    if not priority_csv.exists():
        labeled = phase1 / "first_contact_metrics/contact_metrics_summary_labeled.csv"
        df = pd.read_csv(labeled)
        df = df[
            (df["floating"] == True)
            | (df["contact_status_label"] == "heavy_contact_check_penetration")
        ].copy()
    else:
        df = pd.read_csv(priority_csv)

    rows = []

    for _, row in df.iterrows():
        sid = row["sample_id"]
        src = io_dir / sid
        hand_path = src / "pred_hand_aligned.ply"
        obj_path = src / "pred_object_aligned.ply"

        dst = out_dir / sid
        dst.mkdir(parents=True, exist_ok=True)

        hand = load_geom(hand_path)
        obj = load_geom(obj_path)

        hv = np.asarray(hand.vertices)
        op = object_points(obj)

        tree = cKDTree(op)
        d_m, _ = tree.query(hv, k=1)
        near = hv[d_m < args.contact_mm / 1000.0]

        hand_c = color_geom(hand, [255, 170, 40, 255])
        obj_c = color_geom(obj, [40, 70, 255, 255])
        markers = make_spheres(near)

        parts = [hand_c, obj_c]
        if markers is not None:
            parts.append(markers)

        scene_mesh = trimesh.util.concatenate(parts)
        scene_path = dst / "hand_object_contact_scene.ply"
        scene_mesh.export(scene_path)

        rows.append({
            "sample_id": sid,
            "scene_path": str(scene_path),
            "num_contact_markers": int(len(near)),
            "reason": row.get("inspection_reason", row.get("contact_status_label", "")),
        })

    out_csv = out_dir / "combined_visual_scene_manifest.csv"
    pd.DataFrame(rows).to_csv(out_csv, index=False)

    print("[OK] wrote", out_csv)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
