from __future__ import annotations
import argparse, fnmatch, glob, hashlib, importlib, json, os, subprocess, sys, traceback
from pathlib import Path
from typing import Any

ALLOWED_ENV={'PYTHONPATH','CUDA_VISIBLE_DEVICES','TOKENIZERS_PARALLELISM',
             'PYTORCH_CUDA_ALLOC_CONF'}

def _atomic_json(path: Path, payload: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    os.replace(tmp,path)

def _read_json(path: Path) -> dict[str,Any]:
    return json.loads(path.read_text())

def _sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def _canonical_sha(value: Any) -> str:
    raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(raw).hexdigest()

def _unresolved(value: Any, where: str='root') -> list[str]:
    if isinstance(value,str): return [where] if '$' in value else []
    if isinstance(value,list):
        return sum((_unresolved(item,f'{where}[{index}]') for index,item in enumerate(value)),[])
    if isinstance(value,dict):
        return sum((_unresolved(item,f'{where}.{key}') for key,item in value.items()),[])
    return []

def _matches(spec: dict[str,Any]) -> list[Path]:
    if 'path' in spec:
        path=Path(spec['path'])
        return [path] if path.is_file() and path.stat().st_size>0 else []
    return [Path(p) for p in sorted(glob.glob(spec['glob']))
            if Path(p).is_file() and Path(p).stat().st_size>0]

def _snapshot(specs: list[dict[str,Any]]) -> list[dict[str,Any]]:
    rows=[]
    for spec in specs:
        paths=_matches(spec)
        minimum=int(spec.get('min_count',1))
        if len(paths)<minimum:
            raise RuntimeError(f'expected_output:{spec}:found={len(paths)}:minimum={minimum}')
        for path in paths:
            rows.append({'role':spec['role'],'path':str(path.resolve()),
                         'bytes':path.stat().st_size,'sha256':_sha(path)})
    return rows

def _prefix(spec: dict[str,Any]) -> Path:
    text=spec.get('path') or spec.get('glob') or ''
    for mark in ('*','?','['): text=text.split(mark,1)[0]
    path=Path(text)
    return (path if path.suffix=='' else path.parent).resolve()

def _inside(root: Path, child: Path) -> bool:
    try: return os.path.commonpath([str(root),str(child)])==str(root)
    except ValueError: return False

def _audit_inputs(items: list[dict[str,Any]]) -> list[dict[str,Any]]:
    rows=[]
    for item in items:
        path=Path(item['path'])
        if not path.is_file(): raise RuntimeError('missing_input:'+str(path))
        digest=_sha(path)
        if item.get('sha256') and digest!=item['sha256']:
            raise RuntimeError(f'input_hash:{path}:{digest}:{item["sha256"]}')
        rows.append({'role':item['role'],'path':str(path.resolve()),'sha256':digest})
    return rows

def _declared_by_prior_stage(path: Path, specs: list[dict[str,Any]]) -> bool:
    resolved=str(path.resolve())
    for spec in specs:
        if 'path' in spec and resolved==str(Path(spec['path']).resolve()): return True
        if 'glob' in spec and fnmatch.fnmatch(resolved,str(Path(spec['glob']).resolve())): return True
    return False

def _worker(request_path: Path) -> dict[str,Any]:
    request=_read_json(request_path); receipt=Path(request['worker_receipt'])
    payload={'schema':'tracehoi.FoundationWorkerReceipt.v1',
             'stage':request.get('stage'),'ok':False,'error':None}
    try:
        module_name,function_name=request['callable'].split(':',1)
        function=getattr(importlib.import_module(module_name),function_name)
        function(**request.get('kwargs',{}))
        payload['ok']=True
    except Exception as exc:
        payload['error']={'type':type(exc).__name__,'message':str(exc),
                          'traceback':traceback.format_exc()}
    _atomic_json(receipt,payload)
    return payload

def run_manifest(manifest_path: str|Path, run_root: str|Path,
                 python: str|None=None, dry_run: bool=False) -> dict[str,Any]:
    manifest_path=Path(manifest_path).resolve(); manifest=_read_json(manifest_path)
    run_root=Path(run_root).resolve(); run_root.mkdir(parents=True,exist_ok=True)
    fresh_root=Path(manifest['fresh_output_root']).resolve()
    python=python or sys.executable; errors=[]; completed=[]; children_started=0
    stages=manifest.get('stages',[])
    names=[stage.get('name') for stage in stages]
    if not stages or len(names)!=len(set(names)) or any(not name for name in names):
        errors.append('stage_names')
    unresolved=_unresolved(manifest)
    if unresolved: errors.append('unresolved:'+','.join(unresolved))
    for stage in stages:
        for key in stage.get('env',{}):
            if key not in ALLOWED_ENV: errors.append('disallowed_env:'+key)
        for spec in stage.get('expected_outputs',[]):
            if not _inside(fresh_root,_prefix(spec)):
                errors.append('output_outside_fresh_root:'+repr(spec))
    if errors:
        result={'schema':'tracehoi.FoundationControllerResult.v1','completed':completed,
                'children_started':children_started,'errors':errors,
                'decision':'review_foundation_process_controller'}
        _atomic_json(run_root/'controller_result.json',result); return result
    if dry_run:
        audits=[]; prior_outputs=[]
        for stage in stages:
            try:
                inputs=[]
                for item in stage.get('inputs',[]):
                    path=Path(item['path'])
                    if path.is_file(): inputs.extend(_audit_inputs([item]))
                    elif _declared_by_prior_stage(path,prior_outputs):
                        inputs.append({'role':item['role'],'path':str(path.resolve()),
                                       'status':'declared_by_prior_stage'})
                    else: raise RuntimeError('missing_input:'+str(path))
                preexisting=[]
                for spec in stage['expected_outputs']: preexisting.extend(_matches(spec))
                if preexisting:
                    raise RuntimeError('preexisting_unowned_output:'+','.join(map(str,preexisting)))
                audits.append({'stage':stage['name'],'inputs':inputs})
                prior_outputs.extend(stage['expected_outputs'])
            except Exception as exc:
                errors.append(f'{stage["name"]}:{type(exc).__name__}:{exc}')
        result={'schema':'tracehoi.FoundationControllerResult.v1','completed':audits,
                'children_started':0,'errors':errors,
                'decision':'foundation_process_controller_dry_run_closed'
                           if not errors else 'review_foundation_process_controller'}
        _atomic_json(run_root/'controller_result.json',result); return result

    for index,stage in enumerate(stages):
        name=stage['name']; stage_root=run_root/f'{index:02d}_{name}'
        receipt_path=stage_root/'stage_receipt.json'
        try:
            inputs=_audit_inputs(stage.get('inputs',[]))
            request_core={'stage':name,'callable':stage['callable'],
                          'kwargs':stage.get('kwargs',{}),
                          'input_declarations':stage.get('inputs',[]),
                          'input_snapshot':inputs,
                          'expected_outputs':stage.get('expected_outputs',[])}
            request_sha=_canonical_sha(request_core)
            if receipt_path.is_file():
                prior=_read_json(receipt_path)
                try: outputs=_snapshot(stage['expected_outputs'])
                except RuntimeError: outputs=[]
                if (prior.get('decision')=='foundation_stage_closed'
                    and prior.get('request_sha256')==request_sha
                    and outputs and prior.get('outputs')==outputs):
                    completed.append({'stage':name,'status':'resumed','outputs':outputs})
                    continue
            preexisting=[]
            for spec in stage['expected_outputs']: preexisting.extend(_matches(spec))
            if preexisting:
                raise RuntimeError('preexisting_unowned_output:'+','.join(map(str,preexisting)))

            stage_root.mkdir(parents=True,exist_ok=True)
            worker_receipt=stage_root/'worker_receipt.json'
            request={**request_core,'worker_receipt':str(worker_receipt)}
            request_path=stage_root/'worker_request.json'; _atomic_json(request_path,request)
            env=os.environ.copy(); env.update({str(k):str(v) for k,v in stage.get('env',{}).items()})
            command=[python,str(Path(__file__).resolve()),'--worker-request',str(request_path)]
            try:
                process=subprocess.run(command,capture_output=True,text=True,env=env,check=False,
                                       timeout=stage.get('timeout_seconds'))
                children_started+=1
                (stage_root/'stdout.log').write_text(process.stdout)
                (stage_root/'stderr.log').write_text(process.stderr)
            except subprocess.TimeoutExpired as exc:
                children_started+=1
                stdout=exc.stdout.decode() if isinstance(exc.stdout,bytes) else (exc.stdout or '')
                stderr=exc.stderr.decode() if isinstance(exc.stderr,bytes) else (exc.stderr or '')
                (stage_root/'stdout.log').write_text(stdout)
                (stage_root/'stderr.log').write_text(stderr)
                raise RuntimeError(f'worker_timeout:{stage.get("timeout_seconds")}')
            worker=_read_json(worker_receipt) if worker_receipt.is_file() else {}
            if process.returncode!=0 or not worker.get('ok'):
                raise RuntimeError('worker_failed:'+json.dumps(worker,sort_keys=True))
            outputs=_snapshot(stage['expected_outputs'])
            receipt={'schema':'tracehoi.FoundationStageReceipt.v1','stage':name,
                     'request_sha256':request_sha,'inputs':inputs,'outputs':outputs,
                     'worker_receipt':str(worker_receipt),
                     'decision':'foundation_stage_closed'}
            _atomic_json(receipt_path,receipt)
            completed.append({'stage':name,'status':'executed','outputs':outputs})
        except Exception as exc:
            errors.append(f'{name}:{type(exc).__name__}:{exc}')
            break
    decision=('foundation_process_controller_closed'
              if not errors and len(completed)==len(stages)
              else 'review_foundation_process_controller')
    result={'schema':'tracehoi.FoundationControllerResult.v1','completed':completed,
            'children_started':children_started,'errors':errors,'decision':decision}
    _atomic_json(run_root/'controller_result.json',result); return result

def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--worker-request')
    parser.add_argument('--manifest')
    parser.add_argument('--run-root')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    if args.worker_request:
        result=_worker(Path(args.worker_request))
    elif args.manifest and args.run_root:
        result=run_manifest(args.manifest,args.run_root,dry_run=args.dry_run)
    else:
        result={'decision':'review_foundation_process_controller',
                'errors':['manifest_and_run_root_required']}
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__': main()
