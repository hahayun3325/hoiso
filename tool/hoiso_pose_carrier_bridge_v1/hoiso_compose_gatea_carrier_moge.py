#!/usr/bin/env python3
"""Validate and compose Gate-A -> Hunyuan carrier -> MoGe Sim(3) transforms."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh


def load_transform(path: Path) -> np.ndarray:
    t = np.asarray(np.load(path), dtype=np.float64)
    if t.shape != (4, 4):
        raise ValueError(f"expected 4x4 transform, got {t.shape}: {path}")
    if not np.all(np.isfinite(t)):
        raise ValueError(f"non-finite transform: {path}")
    if not np.allclose(t[3], [0, 0, 0, 1], atol=1e-8):
        raise ValueError(f"invalid homogeneous last row: {path}")
    return t


def sim3_report(t: np.ndarray, label: str, rel_tol: float) -> dict:
    a = t[:3, :3]
    det_a = float(np.linalg.det(a))
    if det_a <= 0:
        return {"label": label, "pass": False, "reason": "non-positive determinant", "det_A": det_a}
    svals = np.linalg.svd(a, compute_uv=False)
    scale = float(np.cbrt(det_a))
    r = a / scale
    spread = float((svals.max() - svals.min()) / max(svals.mean(), 1e-12))
    orth_err = float(np.linalg.norm(r.T @ r - np.eye(3), ord="fro"))
    det_r = float(np.linalg.det(r))
    passed = spread <= rel_tol and abs(det_r - 1.0) <= rel_tol * 10 and orth_err <= rel_tol * 10
    return {
        "label": label,
        "pass": bool(passed),
        "uniform_scale": scale,
        "singular_values": svals.tolist(),
        "relative_singular_spread": spread,
        "det_A": det_a,
        "det_R": det_r,
        "rotation_orthogonality_error": orth_err,
        "translation": t[:3, 3].tolist(),
    }


def load_mesh(path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load(path, process=False)
    if isinstance(loaded, trimesh.Scene):
        dumped = loaded.dump(concatenate=True)
        if isinstance(dumped, trimesh.Trimesh):
            mesh = dumped
        else:
            mesh = trimesh.util.concatenate(tuple(dumped))
    elif isinstance(loaded, trimesh.Trimesh):
        mesh = loaded
    else:
        raise TypeError(f"unsupported mesh type {type(loaded)!r}: {path}")
    if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
        raise ValueError(f"empty mesh: {path}")
    return mesh


def export_mesh(src: Path, dst: Path, transform: np.ndarray) -> dict:
    mesh = load_mesh(src)
    original_vertices = int(len(mesh.vertices))
    original_faces = int(len(mesh.faces))
    mesh.apply_transform(transform)
    mesh.export(dst)
    return {
        "source": str(src),
        "output": str(dst),
        "vertices": original_vertices,
        "faces": original_faces,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--T-g-to-u", type=Path, required=True)
    parser.add_argument("--T-u-to-i", type=Path, required=True)
    parser.add_argument("--gatea-whole", type=Path, required=True)
    parser.add_argument("--gatea-lid", type=Path)
    parser.add_argument("--gatea-base", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--sim3-relative-tolerance", type=float, default=1e-4)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    t_gu = load_transform(args.T_g_to_u)
    t_ui = load_transform(args.T_u_to_i)
    t_gi = t_ui @ t_gu

    reports = [
        sim3_report(t_gu, "T_G_to_Uhoi", args.sim3_relative_tolerance),
        sim3_report(t_ui, "T_Uhoi_to_I", args.sim3_relative_tolerance),
        sim3_report(t_gi, "T_G_to_I", args.sim3_relative_tolerance),
    ]
    if not all(item["pass"] for item in reports):
        (args.out_dir / "transform_validation.json").write_text(
            json.dumps({"status": "HOLD", "transforms": reports}, indent=2) + "\n"
        )
        raise SystemExit("[HOLD] one or more transforms are not proper uniform-scale Sim(3)")

    np.save(args.out_dir / "T_G_to_I.npy", t_gi)
    exports = [
        export_mesh(args.gatea_whole, args.out_dir / "laptop_in_moge.ply", t_gi)
    ]
    if args.gatea_lid:
        exports.append(export_mesh(args.gatea_lid, args.out_dir / "screen_lid_in_moge.ply", t_gi))
    if args.gatea_base:
        exports.append(export_mesh(args.gatea_base, args.out_dir / "keyboard_base_in_moge.ply", t_gi))

    report = {
        "schema": "hoiso_gatea_carrier_moge_composition_v1",
        "status": "PASS",
        "composition_column_vector": "T_G_to_I = T_Uhoi_to_I @ T_G_to_Uhoi",
        "transforms": reports,
        "exports": exports,
    }
    (args.out_dir / "transform_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
