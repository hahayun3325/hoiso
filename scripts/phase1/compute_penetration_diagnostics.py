#!/usr/bin/env python
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
import trimesh
import igl


def load_mesh(path):
    geom = trimesh.load(path, process=False)
    if isinstance(geom, trimesh.Scene):
        geom = trimesh.util.concatenate(tuple(geom.geometry.values()))
    return geom


def vertices_faces(mesh):
    v = np.asarray(mesh.vertices, dtype=np.float64)
    f = np.asarray(mesh.faces, dtype=np.int32)
    return v, f


def winding_number(V, F, Q):
    # Different libigl builds expose slightly different names.
    if hasattr(igl, "fast_winding_number_for_meshes"):
        try:
            return np.asarray(igl.fast_winding_number_for_meshes(V, F, Q))
        except Exception:
            pass

    if hasattr(igl, "winding_number"):
        return np.asarray(igl.winding_number(V, F, Q))

    raise RuntimeError("No winding number function found in igl")


def point_mesh_distance_mm(Q, V, F):
    sqrD, _, _ = igl.point_mesh_squared_distance(Q, V, F)
    return np.sqrt(np.maximum(np.asarray(sqrD), 0.0)) * 1000.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase1-out", default="/home/fredcui/foho_phase0/phase1_diagnostics")
    parser.add_argument("--input-csv", default=None)
    parser.add_argument("--inside-threshold", type=float, default=0.5)
    args = parser.parse_args()

    phase1 = Path(args.phase1_out)
    io_dir = phase1 / "io_alignment"
    out_dir = phase1 / "penetration_diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.input_csv is None:
        input_csv = phase1 / "first_contact_metrics/contact_metrics_summary_labeled.csv"
    else:
        input_csv = Path(args.input_csv)

    df = pd.read_csv(input_csv)

    rows = []

    for _, row in df.iterrows():
        sid = row["sample_id"]
        out = {
            "sample_id": sid,
            "case": row.get("case", ""),
            "method": row.get("method", ""),
            "status": "OK",
            "warnings": "",
        }

        try:
            hand = load_mesh(io_dir / sid / "pred_hand_aligned.ply")
            obj = load_mesh(io_dir / sid / "pred_object_aligned.ply")

            HV, HF = vertices_faces(hand)
            OV, OF = vertices_faces(obj)

            if len(HF) == 0:
                raise ValueError("hand has no faces; cannot use winding penetration")
            if len(OV) == 0:
                raise ValueError("object has no vertices")

            # Main collision signal: object vertices inside hand.
            W_obj_in_hand = winding_number(HV, HF, OV)
            obj_inside = W_obj_in_hand > args.inside_threshold

            obj_depths_mm = point_mesh_distance_mm(OV[obj_inside], HV, HF) if obj_inside.any() else np.array([])

            out["object_vertices_inside_hand"] = int(obj_inside.sum())
            out["object_vertices_total"] = int(len(OV))
            out["object_inside_hand_ratio"] = float(obj_inside.sum() / max(len(OV), 1))
            out["object_inside_hand_max_depth_mm"] = float(obj_depths_mm.max()) if len(obj_depths_mm) else 0.0
            out["object_inside_hand_mean_depth_mm"] = float(obj_depths_mm.mean()) if len(obj_depths_mm) else 0.0

            # Secondary signal: hand vertices inside object.
            # This is less reliable for fragmented / non-watertight generated objects.
            if len(OF) > 0:
                try:
                    W_hand_in_obj = winding_number(OV, OF, HV)
                    hand_inside = W_hand_in_obj > args.inside_threshold
                    hand_depths_mm = point_mesh_distance_mm(HV[hand_inside], OV, OF) if hand_inside.any() else np.array([])

                    out["hand_vertices_inside_object"] = int(hand_inside.sum())
                    out["hand_vertices_total"] = int(len(HV))
                    out["hand_inside_object_ratio"] = float(hand_inside.sum() / max(len(HV), 1))
                    out["hand_inside_object_max_depth_mm"] = float(hand_depths_mm.max()) if len(hand_depths_mm) else 0.0
                    out["hand_inside_object_mean_depth_mm"] = float(hand_depths_mm.mean()) if len(hand_depths_mm) else 0.0

                    if not getattr(obj, "is_watertight", False):
                        out["warnings"] += "object non-watertight; hand-inside-object winding may be unreliable"
                except Exception as e:
                    out["hand_vertices_inside_object"] = ""
                    out["hand_inside_object_ratio"] = ""
                    out["hand_inside_object_max_depth_mm"] = ""
                    out["hand_inside_object_mean_depth_mm"] = ""
                    out["warnings"] += f" hand-inside-object failed: {e}"
            else:
                out["warnings"] += " object has no faces"

        except Exception as e:
            out["status"] = "FAIL"
            out["warnings"] = str(e)

        rows.append(out)

    result = pd.DataFrame(rows)
    out_csv = out_dir / "penetration_diagnostics_summary.csv"
    out_json = out_dir / "penetration_diagnostics_summary.json"

    result.to_csv(out_csv, index=False)
    out_json.write_text(json.dumps(rows, indent=2))

    print("[OK] wrote", out_csv)
    print(result.to_string(index=False))

    if (result["status"] != "OK").any():
        raise SystemExit("Some penetration diagnostics failed")


if __name__ == "__main__":
    main()
