#!/usr/bin/env python
from pathlib import Path
import argparse
import json
import yaml
import numpy as np
import pandas as pd
import trimesh
from scipy.spatial import cKDTree
from rich.console import Console
from rich.table import Table

console = Console()


def load_geometry(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    geom = trimesh.load(path, process=False)

    if isinstance(geom, trimesh.Scene):
        geom = trimesh.util.concatenate(tuple(geom.geometry.values()))

    return geom


def vertices_of(geom):
    return np.asarray(geom.vertices, dtype=np.float64)


def sample_object_points(obj, n=30000):
    """
    First-pass robust object surface representation.

    If object has faces, sample its surface.
    If object is a point cloud or face-less geometry, fall back to vertices.
    """
    if hasattr(obj, "faces") and len(obj.faces) > 0:
        try:
            pts, _ = trimesh.sample.sample_surface(obj, n)
            return np.asarray(pts, dtype=np.float64), "sample_surface"
        except Exception:
            return vertices_of(obj), "vertices_fallback"

    return vertices_of(obj), "vertices_only"


def bbox_center(geom):
    v = vertices_of(geom)
    return 0.5 * (v.min(axis=0) + v.max(axis=0))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/phase1_diagnostics.yaml")
    parser.add_argument("--object-samples", type=int, default=30000)
    args = parser.parse_args()

    cfg = yaml.safe_load(open(args.config, "r"))
    phase1_out = Path(cfg["paths"]["output_dir"])
    io_dir = phase1_out / "io_alignment"
    out_dir = phase1_out / "first_contact_metrics"
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(cfg["paths"]["manifest"])

    contact_m = float(cfg["thresholds_m"]["contact"])
    floating_m = float(cfg["thresholds_m"]["floating"])

    rows = []

    for _, rec in manifest.iterrows():
        sample_id = rec["sample_id"]
        case = rec["case"]
        method = rec["method"]

        row = {
            "sample_id": sample_id,
            "dataset": rec["dataset"],
            "case": case,
            "method": method,
            "status": "OK",
            "warnings": "",
        }

        try:
            hand_path = io_dir / sample_id / "pred_hand_aligned.ply"
            obj_path = io_dir / sample_id / "pred_object_aligned.ply"

            hand = load_geometry(hand_path)
            obj = load_geometry(obj_path)

            hv = vertices_of(hand)
            obj_pts, obj_repr = sample_object_points(obj, args.object_samples)

            if len(hv) == 0:
                raise ValueError("empty hand vertices")
            if len(obj_pts) == 0:
                raise ValueError("empty object points")

            tree = cKDTree(obj_pts)
            dists_m, nn_idx = tree.query(hv, k=1)

            min_m = float(np.min(dists_m))
            p5_m = float(np.percentile(dists_m, 5))
            mean_m = float(np.mean(dists_m))

            contact_mask = dists_m < contact_m
            contact_count = int(contact_mask.sum())
            contact_ratio = float(contact_count / len(hv))

            floating = bool((min_m > floating_m) and (contact_count == 0))

            hand_c = bbox_center(hand)
            obj_c = bbox_center(obj)
            center_dist_m = float(np.linalg.norm(obj_c - hand_c))

            row.update({
                "num_hand_vertices": int(len(hv)),
                "num_object_points_used": int(len(obj_pts)),
                "object_representation": obj_repr,

                "min_hand_object_dist_m": min_m,
                "p5_hand_object_dist_m": p5_m,
                "mean_hand_object_dist_m": mean_m,
                "object_center_to_hand_center_m": center_dist_m,

                "min_hand_object_dist_mm": min_m * 1000.0,
                "p5_hand_object_dist_mm": p5_m * 1000.0,
                "mean_hand_object_dist_mm": mean_m * 1000.0,
                "object_center_to_hand_center_mm": center_dist_m * 1000.0,

                "contact_threshold_mm": contact_m * 1000.0,
                "floating_threshold_mm": floating_m * 1000.0,
                "contact_vertex_count": contact_count,
                "contact_vertex_ratio": contact_ratio,
                "floating": floating,

                # Placeholder for the next substep.
                # Robust penetration needs winding number or SDF logic.
                "penetration_supported": False,
                "penetration_vertex_count": "",
                "max_penetration_depth_mm": "",
            })

            sample_json = out_dir / f"{sample_id}_contact_metrics.json"
            sample_json.write_text(json.dumps(row, indent=2))

        except Exception as e:
            row["status"] = "FAIL"
            row["warnings"] = str(e)

        rows.append(row)

    df = pd.DataFrame(rows)

    out_csv = out_dir / "contact_metrics_summary.csv"
    out_json = out_dir / "contact_metrics_summary.json"

    df.to_csv(out_csv, index=False)
    out_json.write_text(json.dumps(rows, indent=2))

    table = Table(title="Phase 1 Step 2: First Contact Metrics")
    table.add_column("sample_id")
    table.add_column("status")
    table.add_column("min_mm")
    table.add_column("p5_mm")
    table.add_column("mean_mm")
    table.add_column("contact_v")
    table.add_column("floating")
    table.add_column("warnings")

    for _, r in df.iterrows():
        table.add_row(
            str(r["sample_id"]),
            str(r["status"]),
            "" if pd.isna(r.get("min_hand_object_dist_mm")) else f'{r["min_hand_object_dist_mm"]:.2f}',
            "" if pd.isna(r.get("p5_hand_object_dist_mm")) else f'{r["p5_hand_object_dist_mm"]:.2f}',
            "" if pd.isna(r.get("mean_hand_object_dist_mm")) else f'{r["mean_hand_object_dist_mm"]:.2f}',
            "" if pd.isna(r.get("contact_vertex_count")) else str(r["contact_vertex_count"]),
            "" if pd.isna(r.get("floating")) else str(r["floating"]),
            str(r.get("warnings", ""))[:80],
        )

    console.print(table)
    console.print(f"[OK] wrote {out_csv}")
    console.print(f"[OK] wrote {out_json}")

    if (df["status"] != "OK").any():
        raise SystemExit("Some samples failed first contact metrics")


if __name__ == "__main__":
    main()
