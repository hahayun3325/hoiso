#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path

class PhaseConfigError(ValueError):
    pass

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def load_phase_config(path,expected_phase,require_pass=True):
    path=Path(path)
    if not path.is_file(): raise PhaseConfigError(f'missing_phase_config:{path}')
    config=json.loads(path.read_text())
    if not isinstance(config,dict): raise PhaseConfigError('phase_config_must_be_an_object')
    schema=config.get('schema')
    if not isinstance(schema,str) or not schema: raise PhaseConfigError('schema_missing')
    phase=next((config.get(name) for name in ('phase','phase_id','phase_name') if config.get(name) is not None),None)
    if phase!=expected_phase: raise PhaseConfigError(f'unexpected_phase:{phase}')
    if require_pass and config.get('status')!='PASS': raise PhaseConfigError(f'phase_not_PASS:{config.get("status")}')
    if config.get('optimizer_authorized') is not False: raise PhaseConfigError('config_must_not_self_authorize_optimizer')
    allow=config.get('parameter_allowlist')
    if allow is None: allow=config.get('movement_policy',{}).get('parameter_allowlist')
    if not isinstance(allow,dict): raise PhaseConfigError('parameter_allowlist_missing')
    enabled=allow.get('enable',allow.get('trainable')); frozen=allow.get('freeze',allow.get('frozen'))
    if not isinstance(enabled,list) or not enabled: raise PhaseConfigError('enabled_parameter_names_missing')
    if not isinstance(frozen,list) or not frozen: raise PhaseConfigError('frozen_parameter_names_missing')
    for name,row in config.get('sources',{}).items():
        source_path=Path(row.get('path','')); expected=row.get('sha256')
        if not source_path.is_file(): raise PhaseConfigError(f'missing_source:{name}:{source_path}')
        if not expected or digest(source_path)!=expected: raise PhaseConfigError(f'source_hash_mismatch:{name}')
    normalized=dict(config); normalized['_normalized']={'phase':phase,'enabled_parameter_names':enabled,'frozen_parameter_names':frozen}
    return normalized

def resolve_allowlist(config,parameter_registry):
    enabled_names=config['_normalized']['enabled_parameter_names']; missing=[name for name in enabled_names if name not in parameter_registry]
    if missing: raise PhaseConfigError(f'live_parameter_names_unresolved:{missing}')
    selected=[parameter_registry[name] for name in enabled_names]
    if len({id(value) for value in selected})!=len(selected): raise PhaseConfigError('duplicate_live_parameter_owner')
    return selected
