from __future__ import annotations
import argparse,copy,hashlib,json,re
from pathlib import Path
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def bind(input_manifest,output_manifest,receipt,stages,device):
    errors=[]; source=Path(input_manifest); names=[item for item in stages if item]
    if not re.fullmatch(r'[0-9]+',str(device)): errors.append('invalid_GPU_device')
    try: old=json.loads(source.read_text())
    except Exception as exc: old={}; errors.append(f'manifest:{type(exc).__name__}:{exc}')
    new=copy.deepcopy(old); rows=new.get('stages') or []; found=[]; previous=[]
    for row in rows:
        if row.get('name') not in names: continue
        found.append(row.get('name')); kwargs=row.get('kwargs') or {}; args=kwargs.get('runner_args')
        if not isinstance(args,list) or len(args)!=5 or not isinstance(args[4],dict):
            errors.append('runner_args_shape:'+str(row.get('name'))); continue
        previous.append({'stage':row.get('name'),'worker':(row.get('env') or {}).get('CUDA_VISIBLE_DEVICES'),
          'child':args[4].get('CUDA_VISIBLE_DEVICES')})
        args[4]['CUDA_VISIBLE_DEVICES']=str(device)
        row.setdefault('env',{})['CUDA_VISIBLE_DEVICES']=str(device)
    if sorted(found)!=sorted(names): errors.append('stage_coverage:'+str(found)+':'+str(names))
    target=Path(output_manifest)
    if not errors:
        new['GPU_binding']={'stages':names,'CUDA_VISIBLE_DEVICES':str(device),'owner':'foundation_gpu_bind'}
        target.parent.mkdir(parents=True,exist_ok=True); temporary=target.with_suffix('.tmp')
        temporary.write_text(json.dumps(new,indent=2)+'\n'); temporary.replace(target)
    payload={'schema':'tracehoi.FoundationManifestGPUBinding.v1','input':str(source),
      'input_sha256':sha(source) if source.is_file() else None,'output':str(target) if target.is_file() else None,
      'output_sha256':sha(target) if target.is_file() else None,'stages':names,'device':str(device),
      'previous_values':previous,'errors':errors,
      'decision':'foundation_manifest_GPU_binding_closed' if not errors else 'review_foundation_manifest_GPU_binding'}
    receipt_path=Path(receipt)
    receipt_path.parent.mkdir(parents=True,exist_ok=True)
    receipt_path.write_text(json.dumps(payload,indent=2)+'\n'); return payload
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--input',required=True)
    parser.add_argument('--output',required=True); parser.add_argument('--receipt',required=True)
    parser.add_argument('--stages',required=True); parser.add_argument('--device',required=True)
    args=parser.parse_args(); print(json.dumps(bind(args.input,args.output,args.receipt,
      [item.strip() for item in args.stages.split(',')],args.device),indent=2))
if __name__=='__main__': main()
