#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np

from common import (
    load_pickle_npy_dict,
    load_thresholds,
    passes_identity,
    point_metrics,
    reflection_x,
    select_candidate,
    sha256_file,
    shape_metrics,
    to_numpy,
    write_json,
)


DEFAULT_TIPS = np.array([744, 320, 443, 554, 671], dtype=np.int64)
DEFAULT_MAP = np.array([0, 13, 14, 15, 16, 1, 2, 3, 17, 4, 5, 6, 18, 10, 11, 12, 19, 7, 8, 9, 20], dtype=np.int64)


def parser() -> Tuple[argparse.Namespace, list[str]]:
    p = argparse.ArgumentParser(description="Audit saved FollowMyHold/HaMeR H0-H1 keypoint identity.")
    p.add_argument("--batch-npy", default="")
    p.add_argument("--guidance-npy", default="")
    p.add_argument("--j-regressor", default="")
    p.add_argument("--contract-npz", default="")
    p.add_argument("--candidate-index", default="0")
    p.add_argument("--thresholds", default="")
    p.add_argument("--out-dir", default="")
    return p.parse_known_args()


def load_tensor_file(path: Path) -> np.ndarray:
    try:
        import torch

        return np.asarray(to_numpy(torch.load(path, map_location="cpu")))
    except Exception as exc:
        raise RuntimeError(f"Could not load tensor file {path}: {exc}") from exc


def load_contract(args: argparse.Namespace) -> Dict[str, np.ndarray]:
    if args.contract_npz:
        p = Path(args.contract_npz).expanduser().resolve()
        if not p.is_file():
            raise FileNotFoundError(p)
        z = np.load(p, allow_pickle=True)
        required = ["J_regressor", "extra_joints_idxs", "joint_map"]
        missing = [k for k in required if k not in z.files]
        if missing:
            raise KeyError(f"Contract NPZ missing keys: {missing}")
        out = {k: np.asarray(z[k]) for k in z.files}
        out["contract_source"] = np.asarray(str(p))
        return out

    if not args.j_regressor:
        raise ValueError("Provide --contract-npz or --j-regressor")
    p = Path(args.j_regressor).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(p)
    return {
        "J_regressor": load_tensor_file(p),
        "extra_joints_idxs": DEFAULT_TIPS.copy(),
        "joint_map": DEFAULT_MAP.copy(),
        "contract_source": np.asarray(str(p)),
    }


def reconstruct_joints(vertices: np.ndarray, contract: Dict[str, np.ndarray]) -> np.ndarray:
    verts = np.asarray(vertices, dtype=np.float64)
    jreg = np.asarray(contract["J_regressor"], dtype=np.float64)
    tips = np.asarray(contract["extra_joints_idxs"], dtype=np.int64).reshape(-1)
    joint_map = np.asarray(contract["joint_map"], dtype=np.int64).reshape(-1)

    if verts.shape != (778, 3):
        raise ValueError(f"Expected MANO vertices (778,3), got {verts.shape}")
    if jreg.shape[-1] != 778:
        raise ValueError(f"J_regressor must end in 778 vertices, got {jreg.shape}")
    if tips.min() < 0 or tips.max() >= 778:
        raise ValueError(f"Invalid fingertip indices: {tips.tolist()}")

    native = jreg @ verts
    tip_points = verts[tips]
    joints = np.concatenate([native, tip_points], axis=0)
    if joint_map.min() < 0 or joint_map.max() >= joints.shape[0]:
        raise ValueError(f"Invalid joint_map for {joints.shape[0]} joints: {joint_map.tolist()}")
    joints = joints[joint_map]
    if "joint_regressor_extra" in contract:
        extra = np.asarray(contract["joint_regressor_extra"], dtype=np.float64) @ verts
        joints = np.concatenate([joints, extra], axis=0)
    return joints


def scalar_candidate(value: Any, idx: int) -> float:
    x = np.asarray(to_numpy(value)).reshape(-1)
    if idx < 0 or idx >= len(x):
        raise IndexError(f"candidate index {idx} outside scalar array length {len(x)}")
    return float(x[idx])


def main() -> int:
    args, unknown = parser()
    if unknown:
        print(f"[HOLD] Unknown arguments: {unknown}", file=sys.stderr)
        return 1

    try:
        idx = int(args.candidate_index)
    except ValueError:
        print(f"[HOLD] candidate-index must be an integer, got {args.candidate_index}", file=sys.stderr)
        return 1

    if not args.batch_npy:
        print("[HOLD] --batch-npy is required", file=sys.stderr)
        return 1

    batch_path = Path(args.batch_npy).expanduser().resolve()
    guidance_path = Path(args.guidance_npy).expanduser().resolve() if args.guidance_npy else None
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else Path.cwd() / "H0_H1_saved_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    report: Dict[str, Any] = {
        "status": "HOLD_AUDIT_NOT_COMPLETED",
        "stage_scope": ["H0", "H1"],
        "batch_npy": str(batch_path),
        "guidance_npy": str(guidance_path) if guidance_path else None,
        "candidate_index": idx,
        "authorizes_mapping": False,
        "authorizes_mesh_movement": False,
        "authorizes_C2": False,
        "authorizes_F3_4": False,
        "authorizes_Gate_D": False,
    }

    try:
        if not batch_path.is_file():
            raise FileNotFoundError(batch_path)
        batch = load_pickle_npy_dict(batch_path)
        required = ["pred_vertices", "pred_keypoints_3d", "right"]
        missing = [k for k in required if k not in batch]
        if missing:
            raise KeyError(f"Saved HaMeR batch missing keys: {missing}; available={sorted(batch.keys())}")

        contract = load_contract(args)
        thresholds = load_thresholds(args.thresholds or None)

        vertices = select_candidate(batch["pred_vertices"], idx, final_dims=3)
        target_raw = select_candidate(batch["pred_keypoints_3d"], idx, final_dims=3)
        right = int(round(scalar_candidate(batch["right"], idx)))
        multiplier = 2 * right - 1
        helper_raw = reconstruct_joints(vertices, contract)

        h0_direct = point_metrics(target_raw, helper_raw)
        h0_shape = shape_metrics(target_raw, helper_raw)
        h0_reflected = point_metrics(target_raw, reflection_x(helper_raw))
        h0_pass = passes_identity(
            h0_direct,
            max_abs=thresholds["h0_max_abs_m"],
            rmse=thresholds["h0_rmse_m"],
        )

        target_handed = target_raw.copy()
        target_handed[:, 0] *= multiplier
        helper_handed = helper_raw.copy()
        helper_handed[:, 0] *= multiplier
        h1_internal = point_metrics(target_handed, helper_handed)
        h1_internal_pass = passes_identity(
            h1_internal,
            max_abs=thresholds["h1_max_abs_m"],
            rmse=thresholds["h1_rmse_m"],
        )

        h1_guidance = None
        h1_guidance_shape = None
        h1_guidance_reflected = None
        h1_guidance_pass = None
        guidance_keys = None
        if guidance_path:
            if not guidance_path.is_file():
                raise FileNotFoundError(guidance_path)
            guidance = load_pickle_npy_dict(guidance_path)
            guidance_keys = sorted(guidance.keys())
            if "mano_3d_kps" not in guidance:
                raise KeyError(f"Guidance file lacks mano_3d_kps; available={guidance_keys}")
            guidance_3d = np.asarray(to_numpy(guidance["mano_3d_kps"]), dtype=np.float64)
            while guidance_3d.ndim > 2 and guidance_3d.shape[0] == 1:
                guidance_3d = guidance_3d[0]
            h1_guidance = point_metrics(target_handed, guidance_3d)
            h1_guidance_shape = shape_metrics(target_handed, guidance_3d)
            h1_guidance_reflected = point_metrics(target_handed, reflection_x(guidance_3d))
            h1_guidance_pass = passes_identity(
                h1_guidance,
                max_abs=thresholds["h1_max_abs_m"],
                rmse=thresholds["h1_rmse_m"],
            )

        if not h0_pass:
            route = "ROUTE_J_ACTIVE_SOURCE_OR_STATE_MISMATCH"
            status = "HOLD_H0_RAW_JOINT_IDENTITY_FAILED"
        elif not h1_internal_pass:
            route = "ROUTE_J_CHIRALITY_STAGE_MISMATCH"
            status = "HOLD_H1_INTERNAL_HANDEDNESS_IDENTITY_FAILED"
        elif h1_guidance_pass is False:
            route = "ROUTE_J_GUIDANCE_FILE_OR_CANDIDATE_MISMATCH"
            status = "HOLD_H1_GUIDANCE_IDENTITY_FAILED"
        else:
            route = "HOLD_BEFORE_H2_PROJECTION_IDENTITY"
            status = "PASS_H0_H1_CONTINUE_TO_H2"

        report.update(
            {
                "status": status,
                "recommended_route": route,
                "input_hashes": {
                    "batch_npy": sha256_file(batch_path),
                    "guidance_npy": sha256_file(guidance_path) if guidance_path else None,
                    "j_regressor_or_contract": (
                        sha256_file(args.contract_npz) if args.contract_npz else sha256_file(args.j_regressor)
                    ),
                },
                "saved_batch_keys": sorted(batch.keys()),
                "guidance_keys": guidance_keys,
                "right_flag": right,
                "handedness_multiplier": multiplier,
                "contract": {
                    "source": str(contract["contract_source"]),
                    "J_regressor_shape": list(np.asarray(contract["J_regressor"]).shape),
                    "extra_joints_idxs": np.asarray(contract["extra_joints_idxs"]).astype(int).tolist(),
                    "joint_map": np.asarray(contract["joint_map"]).astype(int).tolist(),
                    "has_joint_regressor_extra": "joint_regressor_extra" in contract,
                },
                "thresholds": thresholds,
                "H0": {
                    "description": "raw saved pred_vertices -> source-faithful joints versus raw saved pred_keypoints_3d",
                    "pass": h0_pass,
                    "direct": h0_direct,
                    "shape": h0_shape,
                    "x_reflection_diagnostic": h0_reflected,
                },
                "H1": {
                    "description": "handedness-adjusted source joints versus saved guidance 3D joints",
                    "internal_handedness_pass": h1_internal_pass,
                    "internal": h1_internal,
                    "guidance_pass": h1_guidance_pass,
                    "guidance": h1_guidance,
                    "guidance_shape": h1_guidance_shape,
                    "guidance_x_reflection_diagnostic": h1_guidance_reflected,
                },
                "notes": [
                    "The full HaMeR batch is expected to store raw model/MANO joints before the external handedness flip.",
                    "The guidance file and exported selected mesh are expected to use the handedness-adjusted convention.",
                    "An x-reflection result is diagnostic only; it never authorizes a reflected hand.",
                    "A numerical assignment or permutation is not authorized by this report.",
                ],
            }
        )

        write_json(out_dir / "report.json", report)
        np.save(out_dir / "raw_target_3d.npy", target_raw)
        np.save(out_dir / "raw_reconstructed_3d.npy", helper_raw)
        np.save(out_dir / "handed_target_3d.npy", target_handed)
        np.save(out_dir / "handed_reconstructed_3d.npy", helper_handed)

        print(f"[{ 'PASS' if status.startswith('PASS') else 'HOLD' }] {status}")
        print(f"recommended_route={route}")
        print(out_dir / "report.json")
        return 0 if status.startswith("PASS") else 1
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()
        write_json(out_dir / "report.json", report)
        print(f"[HOLD] Saved HaMeR contract audit failed: {exc}", file=sys.stderr)
        print(out_dir / "report.json", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
