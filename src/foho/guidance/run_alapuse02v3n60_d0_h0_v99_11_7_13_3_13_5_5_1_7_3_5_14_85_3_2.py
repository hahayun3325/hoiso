from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from foho.configs import OptimizationConfig
from foho.guidance.h0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_4 import create_callback
from foho.guidance.h0_callback_launch_bridge_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_1 import invoke_callback_capable_target
from foho.guidance.h0_manifest_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_85_3_9 import H0DiagnosticComplete
from foho.guidance.run import run_hunyuan_w_guid


def _pass_receipt(path):
    if not path:
        return False
    path=Path(path)
    if not path.is_file():
        return False
    return str(json.loads(path.read_text()).get('decision','')).startswith('pass_')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',required=True,choices=('backward-only','capture-only','optimize'))
    parser.add_argument('--call-arguments',required=True)
    parser.add_argument('--output-root',required=True)
    parser.add_argument('--receipt',required=True)
    parser.add_argument('--readiness-receipt',required=True)
    parser.add_argument('--requires-receipt')
    parser.add_argument('--unlock-receipt')
    args=parser.parse_args()

    receipt=Path(args.receipt)
    errors=[]; failed=[]; result={}
    if receipt.exists():
        failed.append('fresh_receipt_required')
    if not _pass_receipt(args.readiness_receipt):
        failed.append('real_binding_readiness_PASS')
    if args.mode=='capture-only' and not _pass_receipt(args.requires_receipt):
        failed.append('backward_only_PASS')
    if args.mode=='optimize' and not _pass_receipt(args.unlock_receipt):
        failed.append('immutable_five_update_unlock_PASS')
    expected={'backward-only':0,'capture-only':0,'optimize':5}[args.mode]
    try:
        if not failed:
            kwargs=json.loads(Path(args.call_arguments).read_text())
            if not isinstance(kwargs,dict):
                raise TypeError('call_arguments_must_be_mapping')
            if 'h0_live_callback' in kwargs or 'config' in kwargs:
                raise ValueError('callback_and_config_are_launcher_owned')
            config_overrides=kwargs.pop('config_overrides',{})
            config=OptimizationConfig()
            for name,value in config_overrides.items():
                if not hasattr(config,name):
                    raise ValueError(f'unknown_config_override:{name}')
                setattr(config,name,value)
            kwargs['config']=config
            callback=create_callback(args.mode,args.output_root)
            try:
                invoke_callback_capable_target(run_hunyuan_w_guid,callback,kwargs)
                failed.append('H0_diagnostic_did_not_terminate_at_H0')
            except H0DiagnosticComplete as complete:
                result=complete.outcome.get('result') or {}
    except Exception as exc:
        errors.append(f'{type(exc).__name__}:{exc}')
    passed=not failed and not errors
    payload={
        'decision':('pass_H0_'+args.mode.replace('-','_') if passed else
                    'review_required_H0_'+args.mode.replace('-','_')),
        'mode':args.mode,'expected_updates':expected,'result':result,
        'optimizer_updates':int(result.get('updates_completed',0)),
        'GPU_used':bool(torch.cuda.is_available()),
        'peak_allocated_bytes':int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else 0,
        'failed':failed,'errors':errors,
    }
    if not receipt.exists():
        receipt.parent.mkdir(parents=True,exist_ok=True)
        receipt.write_text(json.dumps(payload,indent=2,default=str)+'\n')
    print(json.dumps(payload,default=str))


if __name__=='__main__':
    main()
