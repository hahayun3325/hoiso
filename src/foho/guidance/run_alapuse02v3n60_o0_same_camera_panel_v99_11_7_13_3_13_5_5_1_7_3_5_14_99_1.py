from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from foho.configs import OptimizationConfig
from foho.guidance.o0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3 import BypassLegacyHand
from foho.guidance.o0_read_only_same_camera_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_99_1 import (
    O0PanelComplete,
    O0ReadOnlyPanelCallback,
)
from foho.guidance.run import run_hunyuan_w_guid


def _pass(path):
    path = Path(path)
    return path.is_file() and str(json.loads(path.read_text()).get("decision", "")).startswith("pass_")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--call-arguments", required=True)
    parser.add_argument("--case-manifest", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--evaluation", required=True)
    parser.add_argument("--rgb", required=True)
    parser.add_argument("--panel", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--readiness-receipt", required=True)
    args = parser.parse_args()
    receipt = Path(args.receipt)
    failed, errors, result = [], [], {}
    caught = False
    if receipt.exists() or Path(args.panel).exists():
        failed.append("fresh_panel_outputs_required")
    if not _pass(args.readiness_receipt):
        failed.append("O0_panel_readiness_PASS")
    try:
        if not failed:
            kwargs = json.loads(Path(args.call_arguments).read_text())
            overrides = kwargs.pop("config_overrides", {})
            if "h0_live_callback" in kwargs or "o0_live_callback" in kwargs or "config" in kwargs:
                raise ValueError("callbacks_and_config_are_launcher_owned")
            config = OptimizationConfig()
            for name, value in overrides.items():
                if not hasattr(config, name):
                    raise ValueError(f"unknown_config_override:{name}")
                setattr(config, name, value)
            callback = O0ReadOnlyPanelCallback(
                args.case_manifest,
                args.checkpoint,
                args.evaluation,
                args.rgb,
                args.panel,
                args.receipt,
            )
            try:
                run_hunyuan_w_guid(
                    config=config,
                    h0_live_callback=BypassLegacyHand(),
                    o0_live_callback=callback,
                    **kwargs,
                )
                failed.append("O0_panel_did_not_terminate_at_object_seam")
            except O0PanelComplete as complete:
                caught = True
                result = complete.result
    except Exception as exc:
        errors.append(f"{type(exc).__name__}:{exc}")
    passed = not failed and not errors and caught
    payload = {
        "decision": "pass_O0_read_only_panel" if passed else "review_required_O0_read_only_panel",
        "result": result,
        "diagnostic_complete_caught": caught,
        "GPU_used": bool(torch.cuda.is_available()),
        "peak_allocated_bytes": int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else 0,
        "optimizer_updates": 0,
        "failed": failed,
        "errors": errors,
    }
    if not receipt.exists():
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    print(json.dumps(payload, default=str))


if __name__ == "__main__":
    main()
