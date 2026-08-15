#!/usr/bin/env python3
from __future__ import annotations

import argparse
import inspect
import json
import os
import platform
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np

from common import sha256_file, to_numpy, write_json


def safe_parser() -> Tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description="Capture the active HaMeR MANO joint contract without launching Gate C.",
        add_help=True,
    )
    parser.add_argument("--repo", default=os.environ.get("REPO", "/home/fredcui/Projects/FollowMyHold"))
    parser.add_argument("--hamer-root", default="")
    parser.add_argument("--checkpoint", default="")
    parser.add_argument("--out-dir", default="")
    return parser.parse_known_args()


def cfg_get(cfg: Any, dotted: str) -> Any:
    value = cfg
    for part in dotted.split("."):
        try:
            value = value[part]
        except Exception:
            value = getattr(value, part)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return value.tolist()
    except Exception:
        return str(value)


def main() -> int:
    args, unknown = safe_parser()
    if unknown:
        print(f"[HOLD] Unknown arguments: {unknown}", file=sys.stderr)
        return 1

    repo = Path(args.repo).expanduser().resolve()
    hamer_root = Path(args.hamer_root).expanduser().resolve() if args.hamer_root else repo / "third_party/estimator/hamer"
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else Path.cwd() / "active_hamer_contract"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not repo.is_dir():
        print(f"[HOLD] Repository not found: {repo}", file=sys.stderr)
        return 1
    if not hamer_root.is_dir():
        print(f"[HOLD] HaMeR root not found: {hamer_root}", file=sys.stderr)
        return 1

    sys.path.insert(0, str(hamer_root))
    manifest: Dict[str, Any] = {
        "status": "HOLD_CAPTURE_NOT_COMPLETED",
        "repo": str(repo),
        "hamer_root": str(hamer_root),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }

    try:
        import torch
        from hamer.models import DEFAULT_CHECKPOINT, load_hamer

        checkpoint = args.checkpoint or DEFAULT_CHECKPOINT
        model, model_cfg = load_hamer(checkpoint)
        model = model.cpu().eval()
        mano = model.mano

        arrays: Dict[str, np.ndarray] = {
            "J_regressor": np.asarray(to_numpy(mano.J_regressor)),
            "extra_joints_idxs": np.asarray(to_numpy(mano.extra_joints_idxs)),
            "joint_map": np.asarray(to_numpy(mano.joint_map)),
        }
        if hasattr(mano, "joint_regressor_extra"):
            arrays["joint_regressor_extra"] = np.asarray(to_numpy(mano.joint_regressor_extra))

        np.savez_compressed(out_dir / "active_hamer_contract_buffers.npz", **arrays)

        source_files = {}
        for label, obj in {
            "model_class": model.__class__,
            "mano_class": mano.__class__,
            "load_hamer": load_hamer,
        }.items():
            src = inspect.getsourcefile(obj)
            source_files[label] = {
                "path": str(Path(src).resolve()) if src else None,
                "sha256": sha256_file(src) if src and Path(src).is_file() else None,
            }

        checkpoint_path = Path(str(checkpoint)).expanduser()
        checkpoint_info = {
            "value": str(checkpoint),
            "is_local_file": checkpoint_path.is_file(),
            "sha256": sha256_file(checkpoint_path) if checkpoint_path.is_file() else None,
        }

        relevant_cfg = {}
        for key in [
            "MANO.MODEL_PATH",
            "MANO.GENDER",
            "MANO.NUM_HAND_JOINTS",
            "MANO.MEAN_PARAMS",
            "MANO.CREATE_BODY_POSE",
            "MANO.JOINT_REGRESSOR_EXTRA",
            "MODEL.IMAGE_SIZE",
            "EXTRA.FOCAL_LENGTH",
        ]:
            try:
                relevant_cfg[key] = cfg_get(model_cfg, key)
            except Exception:
                relevant_cfg[key] = "<not present>"

        manifest.update(
            {
                "status": "PASS_ACTIVE_HAMER_CONTRACT_CAPTURED",
                "torch": torch.__version__,
                "checkpoint": checkpoint_info,
                "source_files": source_files,
                "model_class": f"{model.__class__.__module__}.{model.__class__.__qualname__}",
                "mano_class": f"{mano.__class__.__module__}.{mano.__class__.__qualname__}",
                "buffers": {name: {"shape": list(arr.shape), "dtype": str(arr.dtype)} for name, arr in arrays.items()},
                "extra_joints_idxs": arrays["extra_joints_idxs"].astype(int).tolist(),
                "joint_map": arrays["joint_map"].astype(int).tolist(),
                "relevant_cfg": relevant_cfg,
                "authorizes_mapping": False,
                "authorizes_mesh_movement": False,
            }
        )
        write_json(out_dir / "active_hamer_contract.json", manifest)
        print("[PASS] Active HaMeR contract captured")
        print(out_dir / "active_hamer_contract.json")
        return 0
    except Exception as exc:
        manifest["error_type"] = type(exc).__name__
        manifest["error"] = str(exc)
        manifest["traceback"] = traceback.format_exc()
        write_json(out_dir / "active_hamer_contract.json", manifest)
        print(f"[HOLD] Active HaMeR contract capture failed: {exc}", file=sys.stderr)
        print(f"See {out_dir / 'active_hamer_contract.json'}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
