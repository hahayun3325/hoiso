from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from foho.configs import OptimizationConfig
from foho.guidance.h0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_4 import CASE_MANIFEST, GLOBAL_POLICY, SOURCE_BUNDLE
from foho.guidance.h0_callback_launch_bridge_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_1 import invoke_callback_capable_target
from foho.guidance.h0_read_only_registration_panel_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_8 import H0PanelComplete, create_panel_callback
from foho.guidance.run import run_hunyuan_w_guid


def _pass(path):
    path = Path(path)
    return path.is_file() and str(json.loads(path.read_text()).get('decision', '')).startswith('pass_')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--call-arguments', required=True)
    parser.add_argument('--output-root', required=True)
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--readiness-receipt', required=True)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--crop', required=True)
    parser.add_argument('--metrics-csv', required=True)
    parser.add_argument('--panel', required=True)
    args = parser.parse_args()
    receipt = Path(args.receipt)
    failed = []; errors = []; result = {}
    if receipt.exists(): failed.append('fresh_receipt_required')
    if Path(args.panel).exists(): failed.append('fresh_panel_required')
    if not _pass(args.readiness_receipt): failed.append('panel_launch_readiness_PASS')
    for label, value in (('call_arguments', args.call_arguments), ('checkpoint', args.checkpoint),
                         ('crop', args.crop), ('metrics_csv', args.metrics_csv)):
        if not Path(value).is_file(): failed.append(f'{label}_exists')
    try:
        if not failed:
            kwargs = json.loads(Path(args.call_arguments).read_text())
            if not isinstance(kwargs, dict): raise TypeError('call_arguments_must_be_mapping')
            if 'h0_live_callback' in kwargs or 'config' in kwargs:
                raise ValueError('callback_and_config_are_launcher_owned')
            overrides = kwargs.pop('config_overrides', {})
            config = OptimizationConfig()
            for name, value in overrides.items():
                if not hasattr(config, name): raise ValueError(f'unknown_config_override:{name}')
                setattr(config, name, value)
            kwargs['config'] = config
            callback = create_panel_callback(CASE_MANIFEST, SOURCE_BUNDLE, GLOBAL_POLICY,
                args.output_root, args.checkpoint, args.crop, args.metrics_csv, args.panel)
            try:
                invoke_callback_capable_target(run_hunyuan_w_guid, callback, kwargs)
                failed.append('panel_did_not_terminate_at_H0')
            except H0PanelComplete as complete:
                result = complete.result
    except Exception as exc:
        errors.append(f'{type(exc).__name__}:{exc}')
    semantic = (result.get('optimizer_updates') == 0 and result.get('new_gradient_count') == 0 and
                result.get('parameters_restored') is True and result.get('gradient_state_restored') is True and
                result.get('frozen_unchanged') is True and Path(result.get('panel_path', '')).is_file())
    if not semantic: failed.append('read_only_panel_semantics_PASS')
    payload = {'decision':('pass_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_8_H0_read_only_panel_process_closed'
                           if not failed and not errors else
                           'review_required_v99_11_7_13_3_13_5_5_1_7_3_5_14_89_8_recheck_H0_read_only_panel_process'),
               'result':result, 'optimizer_updates':0,
               'GPU_used':bool(torch.cuda.is_available()),
               'peak_allocated_bytes':int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else 0,
               'failed':failed, 'errors':errors}
    if not receipt.exists():
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(payload, indent=2, default=str) + '\n')
    print(json.dumps(payload, default=str))


if __name__ == '__main__':
    main()
