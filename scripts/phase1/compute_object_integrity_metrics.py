#!/usr/bin/env python
from pathlib import Path
import numpy as np
import pandas as pd
import trimesh


PHASE1 = Path("/home/fredcui/foho_phase0/phase1_diagnostics")
IO_DIR = PHASE1 / "io_alignment"
MANIFEST = Path("/home/fredcui/Projects/FollowMyHold/data/phase1/manifests/phase1_samples.csv")
OUT_DIR = PHASE1 / "object_integrity_metrics"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_mesh(path):
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh


def bbox_diag_mm(mesh):
    v = np.asarray(mesh.vertices)
    return float(np.linalg.norm(v.max(axis=0) - v.min(axis=0)) * 1000.0)


def main():
    manifest = pd.read_csv(MANIFEST)
    rows = []

    for _, rec in manifest.iterrows():
        sid = rec["sample_id"]
        obj_path = IO_DIR / sid / "pred_object_aligned.ply"

        row = {
            "sample_id": sid,
            "case": rec["case"],
            "method": rec["method"],
            "status": "OK",
            "warnings": "",
        }

        try:
            obj = load_mesh(obj_path)
            faces = getattr(obj, "faces", [])
            verts = getattr(obj, "vertices", [])

            row["num_vertices"] = int(len(verts))
            row["num_faces"] = int(len(faces))
            row["bbox_diag_mm"] = bbox_diag_mm(obj)
            row["is_watertight"] = bool(getattr(obj, "is_watertight", False))

            if len(faces) > 0:
                comps = obj.split(only_watertight=False)
                comp_faces = [len(c.faces) for c in comps]
                comp_verts = [len(c.vertices) for c in comps]

                total_faces = max(sum(comp_faces), 1)
                largest_faces = max(comp_faces) if comp_faces else 0

                row["num_components"] = int(len(comps))
                row["largest_component_faces"] = int(largest_faces)
                row["largest_component_face_ratio"] = float(largest_faces / total_faces)
                row["small_component_count_faces_lt_10"] = int(sum(f < 10 for f in comp_faces))
                row["surface_area"] = float(getattr(obj, "area", 0.0))
            else:
                row["num_components"] = 0
                row["largest_component_faces"] = 0
                row["largest_component_face_ratio"] = 0.0
                row["small_component_count_faces_lt_10"] = 0
                row["surface_area"] = 0.0
                row["warnings"] = "object has no faces"

        except Exception as e:
            row["status"] = "FAIL"
            row["warnings"] = str(e)

        rows.append(row)

    df = pd.DataFrame(rows)
    out_csv = OUT_DIR / "object_integrity_summary.csv"
    df.to_csv(out_csv, index=False)

    print("[OK] wrote", out_csv)
    print(df[[
        "sample_id", "status", "num_components",
        "largest_component_face_ratio",
        "small_component_count_faces_lt_10",
        "bbox_diag_mm", "is_watertight", "warnings"
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
