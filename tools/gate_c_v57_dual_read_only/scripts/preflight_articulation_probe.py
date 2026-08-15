from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np

from common import (
    ProbeConfigError, as_path, ensure_keypoint_pair, keypoint_metrics,
    load_adapter, read_confidence, read_json, read_keypoints, read_manifest,
    write_json,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    try:
        cfg = read_json(args.config)
        thresholds = read_json(as_path(cfg, "thresholds"))
        manifest = read_manifest(as_path(cfg, "parameter_manifest"))
        adapter = load_adapter(as_path(cfg, "adapter"))
        context = adapter.load_context(cfg.get("adapter_context", {}))
        target = read_keypoints(as_path(cfg, "target_keypoints"))
        expected_zero = read_keypoints(as_path(cfg, "expected_zero_keypoints"))
        confidence = read_confidence(cfg.get("confidence") or None, target.shape[0])
        zero = np.asarray(adapter.project_keypoints(context, {}), dtype=np.float64)
        if zero.ndim == 3 and zero.shape[0] == 1:
            zero = zero[0]
        zero = zero[:, :2]
        ensure_keypoint_pair(zero, target, "zero vs target")
        ensure_keypoint_pair(zero, expected_zero, "zero vs expected_zero")

        identity = keypoint_metrics(zero, expected_zero, confidence)
        zthr = thresholds["zero_identity"]
        identity_pass = identity["max_px"] <= float(zthr["max_px"]) and identity["rmse_px"] <= float(zthr["rmse_px"])
        norm_scale = float(cfg.get("normalization_scale_px", 0.0))
        config_ready = np.isfinite(norm_scale) and norm_scale > 0
        result = {
            "status": "PASS" if identity_pass and config_ready else "HOLD",
            "identity_pass": bool(identity_pass),
            "normalization_scale_ready": bool(config_ready),
            "normalization_scale_px": norm_scale,
            "zero_identity_metrics": identity,
            "enabled_parameters": [r["name"] for r in manifest if r["enabled"]],
            "enabled_groups": sorted({r["group"] for r in manifest if r["enabled"]}),
            "adapter_metadata": adapter.metadata(context) if callable(getattr(adapter, "metadata", None)) else {},
            "message": (
                "Ready for finite-difference collection." if identity_pass and config_ready
                else "Do not collect Jacobians until zero identity and normalization scale pass."
            ),
        }
        np.save(out / "zero_projection.npy", zero)
        np.save(out / "target_keypoints.npy", target)
        np.save(out / "confidence.npy", confidence)
        write_json(out / "preflight.json", result)
        print(f"[{result['status']}] {result['message']}")
        return 0
    except ProbeConfigError as exc:
        write_json(out / "preflight.json", {"status": "CONFIG_ERROR", "message": str(exc)})
        print(f"[CONFIG_ERROR] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        write_json(out / "preflight.json", {"status": "ADAPTER_ERROR", "message": repr(exc)})
        print(f"[ADAPTER_ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
