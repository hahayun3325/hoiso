from __future__ import annotations
from dataclasses import dataclass
import hashlib, json
from copy import deepcopy
from pathlib import Path
from typing import Mapping
from foho.automation import q0_binding

class CombinedQ0Error(RuntimeError): pass
def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def _resolve(value: str, roots: Mapping[str,str]) -> Path:
    for token,replacement in roots.items(): value=value.replace(token,replacement)
    if '${' in value: raise CombinedQ0Error(f'unresolved:{value}')
    return Path(value).resolve()
_SCHEMA_KEYWORDS={'$schema','$ref','$defs','type','properties','items','anyOf','oneOf','allOf','enum','const','required','additionalProperties'}
_UNSUPPORTED_STRICT={'allOf','not','dependentRequired','dependentSchemas','if','then','else'}

def _looks_like_json_schema(node: object) -> bool:
    return isinstance(node,dict) and bool(set(node)&_SCHEMA_KEYWORDS)

def _template_schema(node: object, path: str) -> dict:
    if _looks_like_json_schema(node): return _strict_schema(node,path)
    if isinstance(node,dict):
        if not node: raise CombinedQ0Error(f'empty_template_object:{path}')
        if not all(isinstance(key,str) and key for key in node): raise CombinedQ0Error(f'template_keys:{path}')
        properties={key:_template_schema(value,f'{path}.{key}') for key,value in node.items()}
        return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
    if isinstance(node,list):
        if not node: raise CombinedQ0Error(f'empty_template_array:{path}')
        compiled=[_template_schema(value,f'{path}[{index}]') for index,value in enumerate(node)]
        signatures={json.dumps(value,sort_keys=True) for value in compiled}
        if len(signatures)!=1: raise CombinedQ0Error(f'heterogeneous_template_array:{path}')
        return {'type':'array','items':compiled[0]}
    if isinstance(node,bool): return {'type':'boolean'}
    if isinstance(node,int): return {'type':'integer'}
    if isinstance(node,float): return {'type':'number'}
    if isinstance(node,str): return {'type':'string'}
    if node is None: raise CombinedQ0Error(f'untyped_null_template:{path}')
    raise CombinedQ0Error(f'unsupported_template_leaf:{path}:{type(node).__name__}')

def _allows_null(node: dict) -> bool:
    value=node.get('type')
    if value=='null' or isinstance(value,list) and 'null' in value: return True
    return any(isinstance(item,dict) and _allows_null(item) for key in ('anyOf','oneOf') for item in node.get(key,[]) or [])

def _nullable(node: dict) -> dict:
    return node if _allows_null(node) else {'anyOf':[node,{'type':'null'}]}

def _json_scalar_type(value: object, path: str) -> str:
    if value is None: return 'null'
    if isinstance(value,bool): return 'boolean'
    if isinstance(value,int): return 'integer'
    if isinstance(value,float): return 'number'
    if isinstance(value,str): return 'string'
    raise CombinedQ0Error(f'non_scalar_schema_literal:{path}:{type(value).__name__}')

def _enum_type(values: object, path: str) -> object:
    if not isinstance(values,list) or not values: raise CombinedQ0Error(f'empty_or_invalid_enum:{path}')
    kinds={_json_scalar_type(value,f'{path}[{index}]') for index,value in enumerate(values)}
    if kinds <= {'integer','number'}: kinds={'number'}
    non_null=kinds-{'null'}
    if len(non_null)>1: raise CombinedQ0Error(f'heterogeneous_enum_types:{path}:{sorted(kinds)}')
    ordered=sorted(non_null)+(['null'] if 'null' in kinds else [])
    return ordered[0] if len(ordered)==1 else ordered

def audit_openai_transport_schema(node: object, path: str='root', root: bool=True) -> list[str]:
    gaps=[]
    if not isinstance(node,dict): return [f'{path}:not_object']
    forms=set(node)&{'type','$ref','anyOf','oneOf'}
    if not forms: gaps.append(f'{path}:missing_type_or_union')
    value=node.get('type')
    values=set(value) if isinstance(value,list) else ({value} if value is not None else set())
    supported={'string','number','boolean','integer','object','array','null'}
    if values-supported: gaps.append(f'{path}:unsupported_types:{sorted(values-supported)}')
    if root and value!='object': gaps.append(f'{path}:root_not_object')
    properties=node.get('properties')
    if 'object' in values or properties is not None:
        if not isinstance(properties,dict) or not properties: gaps.append(f'{path}:object_properties')
        else:
            if node.get('additionalProperties') is not False: gaps.append(f'{path}:additionalProperties')
            if set(node.get('required',[]) or [])!=set(properties): gaps.append(f'{path}:required')
            for name,child in properties.items(): gaps.extend(audit_openai_transport_schema(child,f'{path}.properties.{name}',False))
    if 'array' in values:
        if 'items' not in node: gaps.append(f'{path}:items')
        else: gaps.extend(audit_openai_transport_schema(node['items'],path+'.items',False))
    for key in ('anyOf','oneOf'):
        choices=node.get(key)
        if key in node and (not isinstance(choices,list) or not choices): gaps.append(f'{path}:{key}')
        for index,child in enumerate(choices or []): gaps.extend(audit_openai_transport_schema(child,f'{path}.{key}[{index}]',False))
    for name,child in (node.get('$defs',{}) or {}).items(): gaps.extend(audit_openai_transport_schema(child,f'{path}.$defs.{name}',False))
    if 'const' in node and 'type' not in node: gaps.append(f'{path}:const_without_type')
    if 'enum' in node and 'type' not in node: gaps.append(f'{path}:enum_without_type')
    return gaps

def _open_object_codec_paths(node: object, path: str) -> dict[str,str]:
    found={}
    if not isinstance(node,dict): return found
    kind=node.get('type')
    kinds=set(kind) if isinstance(kind,list) else ({kind} if kind is not None else set())
    if 'object' in kinds and 'properties' not in node:
        found[path]='nullable_json_object_string' if 'null' in kinds else 'json_object_string'
        return found
    for name,child in (node.get('properties',{}) or {}).items():
        found.update(_open_object_codec_paths(child,f'{path}.{name}'))
    if 'items' in node: found.update(_open_object_codec_paths(node['items'],path+'.items'))
    for keyword in ('anyOf','oneOf'):
        for index,child in enumerate(node.get(keyword,[]) or []):
            found.update(_open_object_codec_paths(child,f'{path}.{keyword}[{index}]'))
    for name,child in (node.get('$defs',{}) or {}).items():
        found.update(_open_object_codec_paths(child,f'{path}.$defs.{name}'))
    return found

def decode_transport_packet(packet: dict, contract: Contract) -> dict:
    if not isinstance(packet,dict): raise CombinedQ0Error('transport_packet_not_object')
    decoded=deepcopy(packet)
    for path,codec in contract.transport_codecs.items():
        if codec not in ('json_object_string','nullable_json_object_string'):
            raise CombinedQ0Error(f'unknown_codec:{path}:{codec}')
        parts=path.split('.'); cursor=decoded
        for part in parts[:-1]:
            if not isinstance(cursor,dict) or part not in cursor:
                raise CombinedQ0Error(f'codec_missing_path:{path}')
            cursor=cursor[part]
        leaf=parts[-1]
        if not isinstance(cursor,dict) or leaf not in cursor:
            raise CombinedQ0Error(f'codec_missing_path:{path}')
        raw=cursor[leaf]
        if raw is None:
            if codec!='nullable_json_object_string':
                raise CombinedQ0Error(f'codec_null_not_allowed:{path}')
            continue
        if not isinstance(raw,str): raise CombinedQ0Error(f'codec_not_string:{path}')
        try: value=json.loads(raw)
        except Exception as exc:
            raise CombinedQ0Error(f'codec_invalid_JSON:{path}:{type(exc).__name__}') from exc
        if not isinstance(value,dict):
            raise CombinedQ0Error(f'codec_decoded_not_object:{path}:{type(value).__name__}')
        cursor[leaf]=value
    return decoded

def _strict_schema(node: object, path: str) -> dict:
    if not isinstance(node,dict): raise CombinedQ0Error(f'schema_node:{path}')
    result=deepcopy(node)
    forbidden=sorted(set(result)&_UNSUPPORTED_STRICT)
    if forbidden: raise CombinedQ0Error(f'unsupported_strict_keywords:{path}:{forbidden}')
    if 'const' in result and 'type' not in result:
        result['type']=_json_scalar_type(result['const'],path+'.const')
    if 'enum' in result and 'type' not in result:
        result['type']=_enum_type(result['enum'],path+'.enum')
    kind=result.get('type')
    kinds=set(kind) if isinstance(kind,list) else ({kind} if kind is not None else set())
    if 'object' in kinds and 'properties' not in result:
        description=str(result.get('description','')).strip()
        suffix='Return a compact JSON object encoded as a string; it is decoded locally before semantic validation.'
        transport_type=['string','null'] if 'null' in kinds else 'string'
        return {'type':transport_type,'description':(description+' '+suffix).strip()}
    properties=result.get('properties')
    if properties is not None:
        if not isinstance(properties,dict) or not properties: raise CombinedQ0Error(f'object_properties:{path}')
        if result.get('type') not in (None,'object'): raise CombinedQ0Error(f'object_type:{path}:{result.get("type")}')
        result['type']='object'
        previous=set(result.get('required',[]) or [])
        if not previous.issubset(properties): raise CombinedQ0Error(f'unknown_required:{path}')
        compiled={}
        for name,child in properties.items():
            value=_strict_schema(child,f'{path}.properties.{name}')
            compiled[name]=value if name in previous else _nullable(value)
        result['properties']=compiled
        result['required']=list(compiled)
        result['additionalProperties']=False
    if result.get('type')=='array':
        if 'items' not in result: raise CombinedQ0Error(f'array_items:{path}')
        result['items']=_strict_schema(result['items'],path+'.items')
    for keyword in ('anyOf','oneOf'):
        if keyword in result:
            choices=result[keyword]
            if not isinstance(choices,list) or not choices: raise CombinedQ0Error(f'{keyword}:{path}')
            result[keyword]=[_strict_schema(child,f'{path}.{keyword}[{index}]') for index,child in enumerate(choices)]
    if '$defs' in result:
        if not isinstance(result['$defs'],dict): raise CombinedQ0Error(f'defs:{path}')
        result['$defs']={name:_strict_schema(child,f'{path}.$defs.{name}') for name,child in result['$defs'].items()}
    return result

def _compile_openai_transport_schema(raw: object, label: str) -> dict:
    base=_strict_schema(raw,label) if _looks_like_json_schema(raw) else _template_schema(raw,label)
    compiled=_strict_schema(base,label)
    gaps=audit_openai_transport_schema(compiled,label,False)
    if gaps: raise CombinedQ0Error(f'transport_schema_gaps:{gaps}')
    return compiled

@dataclass(frozen=True)
class Contract:
    case_id: str; crop: Path; model: str; reasoning_effort: str; store: bool
    consumers: tuple[str,...]; prompt: str; output_schema: dict; owner_hashes: dict[str,str]
    transport_codecs: dict[str,str]

def load_contract(config_path: str|Path, roots: Mapping[str,str]) -> Contract:
    config=json.loads(Path(config_path).read_text())
    if config.get('schema')!='tracehoi.CombinedQ0Contract.v1' or config.get('decision')!='combined_Q0_contract_candidate': raise CombinedQ0Error('config')
    if (config.get('model'),config.get('reasoning_effort'),config.get('store'))!=('gpt-5.6-terra','medium',False): raise CombinedQ0Error('transport')
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
    transport_codecs=_open_object_codec_paths(gate_d0_schema,'gate_d0')
    schema={'type':'object','additionalProperties':False,'required':required,
      'properties':{'object_category':{'type':'string','minLength':1,'maxLength':64},
       'visible_geometry':geometry,'foundation_primary':branches,'foundation_recovery':branches,
       'gate_b':_compile_openai_transport_schema(gate_b['output_schema'],'gate_b'),'gate_d0':_compile_openai_transport_schema(gate_d0_schema,'gate_d0'),
       'confidence':{'type':'number','minimum':0,'maximum':1}}}
    prompt='\n\n'.join([str(q0.get('shared_instruction','')),str(gate_b['system_prompt']),str(gate_b['user_prompt']),
      str(gate_d0_prompt['system_prompt']),str(gate_d0_prompt['user_prompt']),
      'Return short positive keyword lists for: '+', '.join(consumers),
      'For non-null values at these transport fields, return compact JSON object text: '+', '.join(sorted(transport_codecs))])
    return Contract(bound.case_id,bound.crop,config['model'],config['reasoning_effort'],config['store'],consumers,prompt,schema,hashes,transport_codecs)

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
      'transport_codecs':contract.transport_codecs,
      'api_called':False,'gpu_updates':0,'decision':'alapuse02v3n60_combined_Q0_validate_only_closed'}
