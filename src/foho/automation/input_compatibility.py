from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os

class InputContractError(RuntimeError):
    pass

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _resolve(template: str) -> Path:
    expanded=os.path.expandvars(template)
    if '$' in expanded:
        raise InputContractError(f"unresolved_path_template:{template}")
    return Path(expanded).expanduser().resolve()

@dataclass(frozen=True)
class RuntimeInputPacket:
    case_id: str
    rgb: Path
    object_mask: Path
    hand_mask: Path
    official_1000_member: bool
    aggregate_with_official_1000: bool

def load_runtime_input(manifest_path: str | Path) -> RuntimeInputPacket:
    path=Path(manifest_path)
    data=json.loads(path.read_text())
    if data.get('schema')!='tracehoi.RuntimeInputCompatibility.v1':
        raise InputContractError('unexpected_schema')
    if data.get('runtime_decision')!='alapuse_runtime_input_closed':
        raise InputContractError('runtime_input_not_closed')
    resolved={}
    for role in ('rgb','object_mask','hand_mask'):
        item=data.get('inputs',{}).get(role)
        if not isinstance(item,dict): raise InputContractError(f'missing_role:{role}')
        p=_resolve(item.get('path_template',''))
        if not p.is_file(): raise InputContractError(f'missing_file:{role}:{p}')
        if _sha256(p)!=item.get('sha256'): raise InputContractError(f'hash_mismatch:{role}')
        resolved[role]=p
    if len(set(resolved.values()))!=3: raise InputContractError('input_roles_are_not_distinct')
    return RuntimeInputPacket(case_id=data['case_id'],rgb=resolved['rgb'],
        object_mask=resolved['object_mask'],hand_mask=resolved['hand_mask'],
        official_1000_member=bool(data.get('official_1000_member')),
        aggregate_with_official_1000=bool(data.get('aggregate_with_official_1000')))
