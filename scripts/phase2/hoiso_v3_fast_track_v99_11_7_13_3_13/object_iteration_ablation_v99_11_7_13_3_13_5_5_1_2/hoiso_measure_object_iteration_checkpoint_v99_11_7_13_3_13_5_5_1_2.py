#!/usr/bin/env python3
"""Read-only geometric metrics for one object-only checkpoint.

Loads meshes/scenes with node transforms applied, computes basic scale and
hand-relative diagnostics, and writes JSON. It does not modify any asset.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import trimesh
from scipy.spatial import cKDTree


def load_mesh(path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load(path, process=False)
    if isinstance(loaded, trimesh.Scene):
        mesh = loaded.dump(concatenate=True)
    elif isinstance(loaded, trimesh.Trimesh):
        mesh = loaded
    else:
        raise TypeError(f"Unsupported mesh type for {path}: {type(loaded)!r}")
    if not isinstance(mesh, trimesh.Trimesh) or len(mesh.vertices) == 0:
        raise ValueError(f"No usable vertices in {path}")
    return mesh


def vec(value: np.ndarray) -> list[float]:
    return [float(x) for x in np.asarray(value).reshape(-1)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--hand", type=Path, required=True)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--lid", type=Path)
    parser.add_argument("--fingertips", type=Path,
                        help="Optional Nx3 NPY in the same frame as the meshes")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    hand = load_mesh(args.hand)
    obj = load_mesh(args.object)
    hv = np.asarray(hand.vertices, dtype=np.float64)
    ov = np.asarray(obj.vertices, dtype=np.float64)

    if not np.isfinite(hv).all() or not np.isfinite(ov).all():
        raise ValueError("Non-finite mesh vertices")

    htree = cKDTree(hv)
    otree = cKDTree(ov)
    h2o, _ = otree.query(hv, k=1)
    o2h, _ = htree.query(ov, k=1)

    hmin, hmax = hv.min(0), hv.max(0)
    omin, omax = ov.min(0), ov.max(0)
    hext, oext = hmax - hmin, omax - omin
    hdiag, odiag = float(np.linalg.norm(hext)), float(np.linalg.norm(oext))
    hc, oc = hv.mean(0), ov.mean(0)

    report: dict[str, Any] = {
        "label": args.label,
        "hand_path": str(args.hand.resolve()),
        "object_path": str(args.object.resolve()),
        "hand_vertices": int(len(hv)),
        "object_vertices": int(len(ov)),
        "hand_bbox_extents": vec(hext),
        "object_bbox_extents": vec(oext),
        "hand_bbox_diagonal": hdiag,
        "object_bbox_diagonal": odiag,
        "object_to_hand_diagonal_ratio": (odiag / hdiag) if hdiag > 0 else None,
        "hand_center": vec(hc),
        "object_center": vec(oc),
        "object_minus_hand_center": vec(oc - hc),
        "center_distance": float(np.linalg.norm(oc - hc)),
        "hand_to_object": {
            "min": float(np.min(h2o)),
            "p5": float(np.percentile(h2o, 5)),
            "mean": float(np.mean(h2o)),
            "p95": float(np.percentile(h2o, 95)),
        },
        "object_to_hand": {
            "min": float(np.min(o2h)),
            "p5": float(np.percentile(o2h, 5)),
            "mean": float(np.mean(o2h)),
        },
        "object_is_watertight": bool(obj.is_watertight),
        "object_components": int(len(obj.split(only_watertight=False))),
    }

    if args.lid:
        lid = load_mesh(args.lid)
        lv = np.asarray(lid.vertices, dtype=np.float64)
        ltree = cKDTree(lv)
        h2l, _ = ltree.query(hv, k=1)
        report["lid_path"] = str(args.lid.resolve())
        report["hand_to_lid"] = {
            "min": float(np.min(h2l)),
            "p5": float(np.percentile(h2l, 5)),
            "mean": float(np.mean(h2l)),
        }

        if args.fingertips:
            tips = np.load(args.fingertips).astype(np.float64)
            if tips.ndim != 2 or tips.shape[1] != 3:
                raise ValueError(f"Expected Nx3 fingertips, got {tips.shape}")
            t2l, _ = ltree.query(tips, k=1)
            report["fingertips_path"] = str(args.fingertips.resolve())
            report["fingertip_to_lid"] = {
                "per_tip": vec(t2l),
                "min": float(np.min(t2l)),
                "mean": float(np.mean(t2l)),
                "count_within_10mm": int(np.sum(t2l <= 0.010)),
                "count_within_20mm": int(np.sum(t2l <= 0.020)),
            }

    # Contains/penetration is attempted only when the object is watertight.
    if obj.is_watertight:
        try:
            inside = obj.contains(hv)
            report["hand_inside_object"] = {
                "count": int(np.sum(inside)),
                "fraction": float(np.mean(inside)),
            }
        except Exception as exc:  # dependency/topology failures remain explicit
            report["hand_inside_object_error"] = f"{type(exc).__name__}: {exc}"
    else:
        report["hand_inside_object"] = None
        report["hand_inside_object_note"] = "not evaluated because object is non-watertight"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    main()
