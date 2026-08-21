from __future__ import annotations
import argparse,json,os,sys,time
from pathlib import Path
def collect(torch_module=None):
    errors=[]
    try:
        if torch_module is None: import torch as torch_module
        available=bool(torch_module.cuda.is_available()); count=int(torch_module.cuda.device_count())
        names=[str(torch_module.cuda.get_device_name(i)) for i in range(count)]
        torch_version=str(torch_module.__version__); cuda_build=str(torch_module.version.cuda)
    except Exception as exc:
        available=False; count=0; names=[]; torch_version=None; cuda_build=None
        errors.append(f'{type(exc).__name__}:{exc}')
    return {'schema':'tracehoi.FoundationCUDAProbe.v1','python':sys.executable,
      'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES'),
      'torch_version':torch_version,'torch_cuda_build':cuda_build,
      'cuda_available':available,'device_count':count,'device_names':names,
      'foundation_model_loaded':False,'created_unix':time.time(),'errors':errors,
      'decision':'foundation_CUDA_probe_available' if available and count>0 and not errors
                 else 'review_foundation_CUDA_probe'}
def write(output,torch_module=None):
    packet=collect(torch_module); target=Path(output); target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix('.tmp'); temporary.write_text(json.dumps(packet,indent=2)+'\n'); temporary.replace(target)
    return packet
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output',required=True); args=parser.parse_args()
    print(json.dumps(write(args.output),indent=2))
if __name__=='__main__': main()
