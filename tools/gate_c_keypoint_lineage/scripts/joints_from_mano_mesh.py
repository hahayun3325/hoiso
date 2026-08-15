#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
import trimesh

from common import sha256_file, to_numpy, write_json

DEFAULT_TIPS = np.array([744, 320, 443, 554, 671], dtype=np.int64)
DEFAULT_MAP = np.array([0, 13, 14, 15, 16, 1, 2, 3, 17, 4, 5, 6, 18, 10, 11, 12, 19, 7, 8, 9, 20], dtype=np.int64)


def parser() -> Tuple[argparse.Namespace, list[str]]:
    p = argparse.ArgumentParser(description="Derive source-faithful 21 joints from an exact 778-vertex MANO mesh.")
    p.add_argument("--mesh", default="")
    p.add_argument("--j-regressor", default="")
    p.add_argument("--contract-npz", default="")
    p.add_argument("--out-dir", default="")
    return p.parse_known_args()


def load_contract(args: argparse.Namespace) -> Dict[str, np.ndarray]:
    if args.contract_npz:
        z = np.load(Path(args.contract_npz).expanduser().resolve(), allow_pickle=True)
        return {k: np.asarray(z[k]) for k in z.files}
    if not args.j_regressor:
        raise ValueError("Provide --contract-npz or --j-regressor")
    import torch

    return {
        "J_regressor": np.asarray(to_numpy(torch.load(Path(args.j_regressor).expanduser().resolve(), map_location="cpu"))),
        "extra_joints_idxs": DEFAULT_TIPS,
        "joint_map": DEFAULT_MAP,
    }


def reconstruct(verts: np.ndarray, contract: Dict[str, np.ndarray]) -> np.ndarray:
    jreg = np.asarray(contract["J_regressor"], dtype=np.float64)
    tips = np.asarray(contract.get("extra_joints_idxs", DEFAULT_TIPS), dtype=np.int64).reshape(-1)
    mapping = np.asarray(contract.get("joint_map", DEFAULT_MAP), dtype=np.int64).reshape(-1)
    native = jreg @ verts
    combined = np.concatenate([native, verts[tips]], axis=0)
    joints = combined[mapping]
    if "joint_regressor_extra" in contract:
        joints = np.concatenate([joints, np.asarray(contract["joint_regressor_extra"], dtype=np.float64) @ verts], axis=0)
    return joints


def main() -> int:
    args, unknown = parser()
    if unknown:
        print(f"[HOLD] Unknown arguments: {unknown}", file=sys.stderr)
        return 1
    if not args.mesh:
        print("[HOLD] --mesh is required", file=sys.stderr)
        return 1
    mesh_path = Path(args.mesh).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else Path.cwd() / "mano_mesh_joints"
    out_dir.mkdir(parents=True, exist_ok=True)
    report: Dict[str, Any] = {
        "status": "HOLD_MESH_JOINT_EXTRACTION_NOT_COMPLETED",
        "mesh": str(mesh_path),
        "authorizes_mapping": False,
        "authorizes_mesh_movement": False,
    }
    try:
        if not mesh_path.is_file():
            raise FileNotFoundError(mesh_path)
        mesh = trimesh.load(mesh_path, process=False, maintain_order=True)
        if isinstance(mesh, trimesh.Scene):
            geoms = list(mesh.geometry.values())
            if len(geoms) != 1:
                raise ValueError(f"Expected one MANO mesh, found scene with {len(geoms)} geometries")
            mesh = geoms[0]
        verts = np.asarray(mesh.vertices, dtype=np.float64)
        if verts.shape != (778, 3):
            raise ValueError(f"Expected exact MANO topology with 778 ordered vertices, got {verts.shape}")
        contract = load_contract(args)
        joints = reconstruct(verts, contract)
        np.save(out_dir / "mesh_derived_joints.npy", joints)
        report.update(
            {
                "status": "PASS_MESH_DERIVED_JOINTS_WRITTEN",
                "mesh_sha256": sha256_file(mesh_path),
                "vertex_count": int(len(verts)),
                "joint_count": int(len(joints)),
                "J_regressor_shape": list(np.asarray(contract["J_regressor"]).shape),
                "extra_joints_idxs": np.asarray(contract.get("extra_joints_idxs", DEFAULT_TIPS)).astype(int).tolist(),
                "joint_map": np.asarray(contract.get("joint_map", DEFAULT_MAP)).astype(int).tolist(),
                "note": "The mesh is used exactly as stored. No chirality flip, similarity fit, or placement is applied.",
            }
        )
        write_json(out_dir / "report.json", report)
        print("[PASS] Mesh-derived joints written")
        print(out_dir / "mesh_derived_joints.npy")
        return 0
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()
        write_json(out_dir / "report.json", report)
        print(f"[HOLD] Mesh joint extraction failed: {exc}", file=sys.stderr)
        print(out_dir / "report.json", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
