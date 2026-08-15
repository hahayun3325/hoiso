#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import trimesh

from common import load_array, load_thresholds, passes_identity, point_metrics, sha256_file, write_json


def parser() -> Tuple[argparse.Namespace, list[str]]:
    p = argparse.ArgumentParser(
        description=(
            "H4a: verify that the exact ordered 778-vertex source array survived mesh serialization/import unchanged."
        )
    )
    p.add_argument("--source-vertices", default="")
    p.add_argument("--source-key", default="")
    p.add_argument("--candidate", default="0")
    p.add_argument("--mesh", default="")
    p.add_argument("--thresholds", default="")
    p.add_argument("--out", default="")
    return p.parse_known_args()


def load_mesh_vertices(path: Path) -> np.ndarray:
    mesh = trimesh.load(path, process=False, maintain_order=True)
    if isinstance(mesh, trimesh.Scene):
        geoms = list(mesh.geometry.values())
        if len(geoms) != 1:
            raise ValueError(f"Expected one MANO mesh, found {len(geoms)} geometries")
        mesh = geoms[0]
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    if vertices.shape != (778, 3):
        raise ValueError(f"Expected exact 778x3 MANO topology, got {vertices.shape}")
    return vertices


def main() -> int:
    args, unknown = parser()
    if unknown:
        print(f"[HOLD] Unknown arguments: {unknown}", file=sys.stderr)
        return 1
    if not args.source_vertices or not args.mesh:
        print("[HOLD] --source-vertices and --mesh are required", file=sys.stderr)
        return 1
    try:
        candidate = int(args.candidate)
    except ValueError:
        print("[HOLD] --candidate must be an integer", file=sys.stderr)
        return 1

    source_path = Path(args.source_vertices).expanduser().resolve()
    mesh_path = Path(args.mesh).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve() if args.out else Path.cwd() / "H4a_mesh_roundtrip.json"
    report: Dict[str, Any] = {
        "status": "HOLD_H4A_NOT_COMPLETED",
        "stage": "H4a_mesh_serialization_identity",
        "pass": False,
        "authorizes_mapping": False,
        "authorizes_mesh_movement": False,
    }
    try:
        if not source_path.is_file() or not mesh_path.is_file():
            raise FileNotFoundError(f"source={source_path.is_file()} mesh={mesh_path.is_file()}")
        source = load_array(source_path, args.source_key or None, candidate)
        if source.shape != (778, 3):
            raise ValueError(f"Expected 778x3 source vertices, got {source.shape}")
        serialized = load_mesh_vertices(mesh_path)
        metrics = point_metrics(source, serialized)
        thresholds = load_thresholds(args.thresholds or None)
        passed = passes_identity(metrics, thresholds["h4_max_abs_m"], thresholds["h4_rmse_m"])
        report.update(
            {
                "status": "PASS_H4A_MESH_SERIALIZATION_IDENTITY" if passed else "HOLD_H4A_MESH_SERIALIZATION_FAILED",
                "pass": passed,
                "metrics": metrics,
                "thresholds_used": {
                    "max_abs_coordinate_error": thresholds["h4_max_abs_m"],
                    "rmse": thresholds["h4_rmse_m"],
                },
                "hashes": {"source_vertices": sha256_file(source_path), "mesh": sha256_file(mesh_path)},
                "note": (
                    "This test detects remeshing, decimation, vertex reordering, scale changes, and export/import drift. "
                    "It does not test joint semantics."
                ),
            }
        )
        write_json(out_path, report)
        print(f"[{'PASS' if passed else 'HOLD'}] {report['status']}")
        print(out_path)
        return 0 if passed else 1
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()
        write_json(out_path, report)
        print(f"[HOLD] H4a roundtrip failed: {exc}", file=sys.stderr)
        print(out_path, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
