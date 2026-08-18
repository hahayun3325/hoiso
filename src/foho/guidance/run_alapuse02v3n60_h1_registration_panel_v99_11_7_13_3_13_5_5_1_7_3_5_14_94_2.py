from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from foho.configs import OptimizationConfig
from foho.guidance.h0_callback_launch_bridge_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_1 import invoke_callback_capable_target
from foho.guidance.h1_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_90_5 import PATHS
from foho.guidance.h1_read_only_registration_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_94_2 import H1PanelComplete, create_h1_panel_callback
from foho.guidance.run import run_hunyuan_w_guid


def _passed(path):
    path = Path(path)
    return path.is_file() and str(json.loads(path.read_text()).get('decision', '')).startswith('pass_')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--call-arguments', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--metrics', required=True)
    parser.add_argument('--crop-path', required=True)
    parser.add_argument('--panel', required=True)
    parser.add_argument('--readiness-receipt', required=True)
    parser.add_argument('--receipt', required=True)
    args = parser.parse_args()
    receipt = Path(args.receipt)
    panel = Path(args.panel)
    failed = []
    errors = []
    result = {}
    caught = False
    if receipt.exists():
        failed.append('fresh_receipt_required')
    if panel.exists():
        failed.append('fresh_panel_required')
    if not _passed(args.readiness_receipt):
        failed.append('H1_panel_readiness_PASS')
    try:
        if not failed:
            kwargs = json.loads(Path(args.call_arguments).read_text())
            if not isinstance(kwargs, dict):
                raise TypeError('call_arguments_must_be_mapping')
            if 'h0_live_callback' in kwargs or 'config' in kwargs:
                raise ValueError('callback_and_config_are_launcher_owned')
            config = OptimizationConfig()
            for name, value in kwargs.pop('config_overrides', {}).items():
                if not hasattr(config, name):
                    raise ValueError(f'unknown_config_override:{name}')
                setattr(config, name, value)
            kwargs['config'] = config
            callback = create_h1_panel_callback(
                PATHS, args.output_root, args.checkpoint, args.crop_path,
                args.metrics, args.panel)
            try:
                invoke_callback_capable_target(run_hunyuan_w_guid, callback, kwargs)
                failed.append('H1_panel_did_not_terminate_at_hand_seam')
            except H1PanelComplete as complete:
                caught = True
                result = complete.result
    except Exception as exc:
        errors.append(f'{type(exc).__name__}:{exc}')
    semantic = (caught and result.get('optimizer_updates') == 0 and
                result.get('checkpoint_writes') == 0 and
                result.get('parameter_restored') is True and
                result.get('frozen_unchanged') is True and panel.is_file())
    if not semantic:
        failed.append('read_only_panel_semantics_PASS')
    payload = {'decision': ('pass_H1_read_only_same_camera_panel' if not failed and not errors
                            else 'review_required_H1_read_only_same_camera_panel'),
               'result': result, 'diagnostic_complete_caught': caught,
               'H1': {'authorized': 1, 'spent': 1, 'executable': False},
               'GPU_used': bool(torch.cuda.is_available()), 'optimizer_updates': 0,
               'peak_allocated_bytes': int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else 0,
               'failed': failed, 'errors': errors}
    if not receipt.exists():
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(payload, indent=2, default=str) + '\n')
    print(json.dumps(payload, default=str))


if __name__ == '__main__':
    main()
