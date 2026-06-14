#!/usr/bin/env python
from pathlib import Path
import argparse
import json
import yaml
import pandas as pd
from rich.console import Console
from rich.table import Table

from hoi_diagnostics.io import load_manifest, load_geometry, load_similarity_transform
from hoi_diagnostics.alignment import apply_similarity, bbox_diag
from hoi_diagnostics.sanity import assert_geometry_basic, assert_hand_bbox_m

console = Console()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/phase1_diagnostics.yaml")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    cfg = yaml.safe_load(open(args.config, "r"))

    manifest_path = Path(cfg["paths"]["manifest"])
    out_dir = Path(cfg["paths"]["output_dir"]) / "io_alignment"
    out_dir.mkdir(parents=True, exist_ok=True)

    records = load_manifest(manifest_path)
    if args.limit:
        records = records[: args.limit]

    table = Table(title="Phase 1 Step 1: I/O + Alignment Sanity")
    table.add_column("sample_id")
    table.add_column("status")
    table.add_column("hand_diag_mm")
    table.add_column("obj_diag_mm")
    table.add_column("sim_scale")
    table.add_column("warnings")

    rows = []

    for rec in records:
        status = "OK"
        warnings = []
        hand_diag_m = float("nan")
        obj_diag_m = float("nan")
        scale = float("nan")

        try:
            pred_hand = load_geometry(rec.pred_hand_mesh)
            pred_obj = load_geometry(rec.pred_object_mesh)
            gt_hand = load_geometry(rec.gt_hand_mesh)
            gt_obj = load_geometry(rec.gt_object_mesh)

            scale, R, t, transform_keys = load_similarity_transform(rec.align_npz)

            pred_hand_aligned = apply_similarity(pred_hand, scale, R, t)
            pred_obj_aligned = apply_similarity(pred_obj, scale, R, t)

            warnings += assert_geometry_basic(pred_hand_aligned, f"{rec.sample_id}/pred_hand_aligned")
            warnings += assert_geometry_basic(pred_obj_aligned, f"{rec.sample_id}/pred_obj_aligned")
            warnings += assert_geometry_basic(gt_hand, f"{rec.sample_id}/gt_hand")
            warnings += assert_geometry_basic(gt_obj, f"{rec.sample_id}/gt_obj")

            hand_diag_m = assert_hand_bbox_m(
                pred_hand_aligned,
                rec.sample_id,
                cfg["units"]["hand_bbox_diag_min_m"],
                cfg["units"]["hand_bbox_diag_max_m"],
            )

            obj_diag_m = bbox_diag(pred_obj_aligned)

            if cfg["debug"].get("save_aligned_meshes", True):
                sample_dir = out_dir / rec.sample_id
                sample_dir.mkdir(parents=True, exist_ok=True)
                pred_hand_aligned.export(sample_dir / "pred_hand_aligned.ply")
                pred_obj_aligned.export(sample_dir / "pred_object_aligned.ply")

        except Exception as e:
            status = "FAIL"
            warnings.append(str(e))
            if cfg["debug"].get("fail_fast", False):
                raise

        row = {
            "sample_id": rec.sample_id,
            "dataset": rec.dataset,
            "case": rec.case,
            "method": rec.method,
            "status": status,
            "hand_diag_m": hand_diag_m,
            "hand_diag_mm": hand_diag_m * 1000.0 if hand_diag_m == hand_diag_m else None,
            "object_diag_m": obj_diag_m,
            "object_diag_mm": obj_diag_m * 1000.0 if obj_diag_m == obj_diag_m else None,
            "sim_scale": scale,
            "pred_hand_mesh": str(rec.pred_hand_mesh),
            "pred_object_mesh": str(rec.pred_object_mesh),
            "gt_hand_mesh": str(rec.gt_hand_mesh),
            "gt_object_mesh": str(rec.gt_object_mesh),
            "align_npz": str(rec.align_npz),
            "warnings": " | ".join(warnings),
        }
        rows.append(row)

        table.add_row(
            rec.sample_id,
            status,
            "nan" if row["hand_diag_mm"] is None else f'{row["hand_diag_mm"]:.2f}',
            "nan" if row["object_diag_mm"] is None else f'{row["object_diag_mm"]:.2f}',
            "nan" if scale != scale else f"{scale:.4f}",
            row["warnings"][:100],
        )

    console.print(table)

    out_csv = out_dir / "io_alignment_summary.csv"
    out_json = out_dir / "io_alignment_summary.json"

    pd.DataFrame(rows).to_csv(out_csv, index=False)
    out_json.write_text(json.dumps(rows, indent=2))

    print("[OK] wrote", out_csv)
    print("[OK] wrote", out_json)

    n_fail = sum(r["status"] != "OK" for r in rows)
    if n_fail:
        raise SystemExit(f"[FAIL] {n_fail} samples failed I/O/alignment sanity")
    print("[OK] all samples passed")


if __name__ == "__main__":
    main()
