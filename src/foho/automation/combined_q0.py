from __future__ import annotations
from dataclasses import dataclass
import hashlib, json
from pathlib import Path
from typing import Mapping
from foho.automation import q0_binding

class CombinedQ0Error(RuntimeError): pass
def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def _resolve(value: str, roots: Mapping[str,str]) -> Path:
    for token,replacement in roots.items(): value=value.replace(token,replacement)
    if '${' in value: raise CombinedQ0Error(f'unresolved:{value}')
    return Path(value).resolve()
@dataclass(frozen=True)
class Contract:
    case_id: str; crop: Path; model: str; reasoning_effort: str; store: bool
    consumers: tuple[str,...]; prompt: str; output_schema: dict; owner_hashes: dict[str,str]

def load_contract(config_path: str|Path, roots: Mapping[str,str]) -> Contract:
    config=json.loads(Path(config_path).read_text())
    if config.get('schema')!='tracehoi.CombinedQ0Contract.v1' or config.get('decision')!='combined_Q0_contract_candidate': raise CombinedQ0Error('config')
    if (config.get('model'),config.get('reasoning_effort'),config.get('store'))!=('gpt-5.5-2026-04-23','high',False): raise CombinedQ0Error('transport')
    paths={}; hashes={}
    for role,item in config.get('owners',{}).items():
        path=_resolve(item['path_template'],roots)
        if not path.is_file(): raise CombinedQ0Error(f'missing:{role}:{path}')
        actual=_sha(path)
        if actual!=item['sha256']: raise CombinedQ0Error(f'hash:{role}:{actual}')
        paths[role]=path; hashes[role]=actual
    if Path(q0_binding.__file__).resolve()!=paths['q0_binding_source']:
        raise CombinedQ0Error(f'q0_module_owner:{q0_binding.__file__}:{paths["q0_binding_source"]}')
    bound=q0_binding.bind_q0(paths['q0_binding_config'],roots)
    q0=json.loads(paths['q0_design'].read_text()); policy=json.loads(paths['foundation_policy'].read_text())
    gate_b=json.loads(paths['gate_b_prompt'].read_text()); gate_d0_prompt=json.loads(paths['gate_d0_prompt'].read_text())
    gate_d0_schema=json.loads(paths['gate_d0_schema'].read_text())
    if set(('system_prompt','user_prompt','output_schema'))-set(gate_b): raise CombinedQ0Error('gate_b_owner_keys')
    if set(('system_prompt','user_prompt','output_schema'))-set(gate_d0_prompt): raise CombinedQ0Error('gate_d0_prompt_owner_keys')
    consumers=tuple(config['foundation_consumers'])
    live=tuple(sorted(name for name,item in policy.get('consumers',{}).items() if item.get('kind')=='text'))
    if tuple(sorted(consumers))!=live: raise CombinedQ0Error(f'consumers:{consumers}:{live}')
    if q0.get('required_output_sections')!=config['required_output_sections']: raise CombinedQ0Error('required_sections')
    keyword={'type':'array','minItems':1,'maxItems':8,'items':{'type':'string','minLength':1,'maxLength':64}}
    branches={'type':'object','additionalProperties':False,'required':list(consumers),'properties':{name:dict(keyword) for name in consumers}}
    geometry={'type':'object','additionalProperties':False,
      'required':['articulated','articulation_state','visible_parts','occlusion_summary'],
      'properties':{'articulated':{'type':'boolean'},
       'articulation_state':{'type':'string','enum':['OPEN','CLOSED','UNCERTAIN','NOT_APPLICABLE']},
       'visible_parts':{'type':'array','maxItems':12,'items':{'type':'string','maxLength':64}},
       'occlusion_summary':{'type':'string','maxLength':240}}}
    required=config['required_output_sections']
    schema={'type':'object','additionalProperties':False,'required':required,
      'properties':{'object_category':{'type':'string','minLength':1,'maxLength':64},
       'visible_geometry':geometry,'foundation_primary':branches,'foundation_recovery':branches,
       'gate_b':gate_b['output_schema'],'gate_d0':gate_d0_schema,
       'confidence':{'type':'number','minimum':0,'maximum':1}}}
    prompt='\n\n'.join([str(q0.get('shared_instruction','')),str(gate_b['system_prompt']),str(gate_b['user_prompt']),
      str(gate_d0_prompt['system_prompt']),str(gate_d0_prompt['user_prompt']),
      'Return short positive keyword lists for: '+', '.join(consumers)])
    return Contract(bound.case_id,bound.crop,config['model'],config['reasoning_effort'],config['store'],consumers,prompt,schema,hashes)

def validate_semantic_packet(packet: dict, contract: Contract) -> None:
    if set(packet)!=set(contract.output_schema['required']): raise CombinedQ0Error(f'top_level_keys:{sorted(packet)}')
    for branch in ('foundation_primary','foundation_recovery'):
        if set(packet.get(branch,{}))!=set(contract.consumers): raise CombinedQ0Error(f'{branch}_keys')

def validation_receipt(contract: Contract) -> dict:
    return {'schema':'tracehoi.CombinedQ0ValidationReceipt.v1','case_id':contract.case_id,
      'crop':str(contract.crop),'crop_sha256':_sha(contract.crop),'model':contract.model,
      'reasoning_effort':contract.reasoning_effort,'store':contract.store,
      'prompt_sha256':hashlib.sha256(contract.prompt.encode()).hexdigest(),
      'output_schema_sha256':hashlib.sha256(json.dumps(contract.output_schema,sort_keys=True).encode()).hexdigest(),
      'foundation_consumers':list(contract.consumers),'owner_hashes':contract.owner_hashes,
      'api_called':False,'gpu_updates':0,'decision':'alapuse02v3n60_combined_Q0_validate_only_closed'}
