from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, os
from pathlib import Path
from typing import Mapping
from foho.automation.input_compatibility import load_runtime_input

class Q0BindingError(RuntimeError): pass
def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def _resolve(template: str, roots: Mapping[str,str]) -> Path:
    value=template
    for token,replacement in roots.items(): value=value.replace(token,replacement)
    if value.startswith('$') or '${' in value: raise Q0BindingError(f'unresolved_owner:{template}')
    return Path(value).resolve()
@dataclass(frozen=True)
class BoundQ0:
    case_id: str
    crop: Path
    model: str
    reasoning_effort: str
    store: bool
    expected_output_sections: tuple[str,...]
    owner_hashes: dict[str,str]
def bind_q0(config_path: str|Path, roots: Mapping[str,str]) -> BoundQ0:
    config=json.loads(Path(config_path).read_text())
    if config.get('schema')!='tracehoi.RealInputQ0Binding.v1': raise Q0BindingError('schema')
    if config.get('decision')!='real_input_Q0_binding_candidate': raise Q0BindingError('candidate_not_closed')
    if config.get('case_id')!='alapuse02v3n60': raise Q0BindingError('case')
    if (config.get('model'),config.get('reasoning_effort'),config.get('store')) != ('gpt-5.6-terra','medium',False):
        raise Q0BindingError('transport')
    paths={}; hashes={}
    for role,item in config.get('owners',{}).items():
        path=_resolve(item['path_template'],roots)
        if not path.is_file(): raise Q0BindingError(f'missing:{role}:{path}')
        actual=_sha(path)
        if actual!=item['sha256']: raise Q0BindingError(f'hash:{role}:{actual}')
        paths[role]=path; hashes[role]=actual
    runtime=load_runtime_input(paths['runtime_input_manifest'])
    if runtime.case_id!=config['case_id']: raise Q0BindingError('input_case')
    return BoundQ0(runtime.case_id,runtime.rgb,config['model'],config['reasoning_effort'],
                   config['store'],tuple(config['expected_output_sections']),hashes)
def validation_receipt(bound: BoundQ0) -> dict:
    return {'schema':'tracehoi.RealInputQ0BindingReceipt.v1','case_id':bound.case_id,
     'crop':str(bound.crop),'crop_sha256':_sha(bound.crop),'model':bound.model,
     'reasoning_effort':bound.reasoning_effort,'store':bound.store,
     'expected_output_sections':list(bound.expected_output_sections),
     'owner_hashes':bound.owner_hashes,'api_called':False,'gpu_updates':0,
     'decision':'real_input_Q0_binding_validate_only_closed'}
