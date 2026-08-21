from __future__ import annotations
import hashlib, json, os
from pathlib import Path
from typing import Any

def _sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def _atomic(path: Path, payload: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    os.replace(temp,path)

def _inventory(roots: list[str], receipt: Path) -> list[dict[str,Any]]:
    rows=[]
    for raw in roots:
        root=Path(raw).resolve()
        files=sorted(path for path in root.rglob('*')
                     if path.is_file() and path.stat().st_size>0
                     and path.resolve()!=receipt.resolve())
        if not files: raise RuntimeError('empty output root: '+str(root))
        rows.append({'root':str(root),'files':[{
          'path':str(path.resolve()),'bytes':path.stat().st_size,'sha256':_sha(path)}
          for path in files]})
    return rows

def run(*, runner_args: list[Any], runner_kwargs: dict[str,Any]|None=None,
        output_roots: list[str]|None=None, output_receipt: str|None=None) -> None:
    if not isinstance(runner_args,list): raise TypeError('runner_args must be a list')
    if runner_kwargs is None: runner_kwargs={}
    if not isinstance(runner_kwargs,dict): raise TypeError('runner_kwargs must be a dict')
    if output_roots is not None and not isinstance(output_roots,list):
        raise TypeError('output_roots must be a list')
    from foho.utils.runner import run_in_conda
    result=run_in_conda(*runner_args,**runner_kwargs)
    returncode=getattr(result,'returncode',None)
    if returncode is None and isinstance(result,int) and not isinstance(result,bool):
        returncode=result
    if returncode not in (None,0):
        raise RuntimeError(f'run_in_conda returned nonzero status: {returncode}')
    if output_roots is not None:
        if not output_receipt: raise ValueError('output_receipt is required')
        receipt=Path(output_receipt)
        roots=_inventory(output_roots,receipt)
        _atomic(receipt,{'schema':'tracehoi.FoundationStageArtifactInventory.v1',
          'output_roots':roots,'file_count':sum(len(row['files']) for row in roots),
          'decision':'foundation_stage_artifact_inventory_closed'})
