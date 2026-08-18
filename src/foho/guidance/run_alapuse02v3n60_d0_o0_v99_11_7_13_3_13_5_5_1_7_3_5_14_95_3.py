from __future__ import annotations
import argparse,json
from pathlib import Path
import torch
from foho.configs import OptimizationConfig
from foho.guidance.o0_alapuse02v3n60_real_binding_v99_11_7_13_3_13_5_5_1_7_3_5_14_95_3 import O0DiagnosticComplete,create_callback
from foho.guidance.run import run_hunyuan_w_guid

def _pass(path):
    path=Path(path) if path else None
    return bool(path and path.is_file() and str(json.loads(path.read_text()).get('decision','')).startswith('pass_'))
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--mode',required=True,choices=('backward-only','capture-only','optimize'))
    parser.add_argument('--call-arguments',required=True); parser.add_argument('--case-manifest',required=True)
    parser.add_argument('--output-root',required=True); parser.add_argument('--receipt',required=True)
    parser.add_argument('--readiness-receipt',required=True); parser.add_argument('--requires-receipt'); parser.add_argument('--unlock-receipt')
    args=parser.parse_args(); receipt=Path(args.receipt); failed=[]; errors=[]; result={}; caught=False
    if receipt.exists(): failed.append('fresh_receipt_required')
    if not _pass(args.readiness_receipt): failed.append('O0_binding_readiness_PASS')
    if args.mode=='capture-only' and not _pass(args.requires_receipt): failed.append('O0_backward_PASS')
    if args.mode=='optimize' and not _pass(args.unlock_receipt): failed.append('O0_immutable_unlock_PASS')
    try:
        if not failed:
            kwargs=json.loads(Path(args.call_arguments).read_text()); overrides=kwargs.pop('config_overrides',{})
            if 'h0_live_callback' in kwargs or 'o0_live_callback' in kwargs or 'config' in kwargs: raise ValueError('callbacks_and_config_are_launcher_owned')
            config=OptimizationConfig()
            for name,value in overrides.items():
                if not hasattr(config,name): raise ValueError(f'unknown_config_override:{name}')
                setattr(config,name,value)
            hand_bypass,o0=create_callback(args.mode,args.output_root,args.case_manifest)
            try:
                run_hunyuan_w_guid(config=config,h0_live_callback=hand_bypass,o0_live_callback=o0,**kwargs)
                failed.append('O0_diagnostic_did_not_terminate_at_object_seam')
            except O0DiagnosticComplete as complete:
                caught=True; result=complete.outcome.get('result') or {}
    except Exception as exc: errors.append(f'{type(exc).__name__}:{exc}')
    expected={'backward-only':0,'capture-only':0,'optimize':5}[args.mode]
    passed=not failed and not errors and caught
    payload={'decision':('pass_O0_'+args.mode.replace('-','_') if passed else 'review_required_O0_'+args.mode.replace('-','_')),
      'mode':args.mode,'expected_attempts':expected,'result':result,'diagnostic_complete_caught':caught,
      'optimizer_updates':int(result.get('updates_completed',0)),'GPU_used':bool(torch.cuda.is_available()),
      'peak_allocated_bytes':int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else 0,
      'failed':failed,'errors':errors}
    if not receipt.exists(): receipt.parent.mkdir(parents=True,exist_ok=True); receipt.write_text(json.dumps(payload,indent=2,default=str)+'\n')
    print(json.dumps(payload,default=str))
if __name__=='__main__': main()
