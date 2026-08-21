from __future__ import annotations
import argparse,base64,hashlib,json,mimetypes,os
from pathlib import Path
from typing import Any

STAGES=('get_hunyuan_input','inpaint','moge','hunyuan','hamer','h2m','mano_registration')

def sha(path: str|Path)->str:
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def atomic(path: str|Path,payload: dict[str,Any])->None:
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix(target.suffix+'.tmp')
    temp.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n'); os.replace(temp,target)

def schema(case_id: str)->dict[str,Any]:
    stage={'type':'object','additionalProperties':False,
      'properties':{'stage':{'type':'string','enum':list(STAGES)},
       'status':{'type':'string','enum':['PASS','FAIL','UNCERTAIN']},
       'confidence':{'type':'number','minimum':0,'maximum':1},
       'evidence':{'type':'string'}},
      'required':['stage','status','confidence','evidence']}
    return {'type':'object','additionalProperties':False,
      'properties':{'case_id':{'type':'string','enum':[case_id]},
       'overall_decision':{'type':'string','enum':['PASS','REJECT_CASE']},
       'stage_decisions':{'type':'array','items':stage,'minItems':7,'maxItems':7},
       'retry_owner':{'type':'string','enum':['none']},
       'recheck_required':{'type':'boolean','enum':[False]},
       'recommended_recovery_prompt':{'type':'string','enum':['']},
       'summary':{'type':'string'}},
      'required':['case_id','overall_decision','stage_decisions','retry_owner',
                  'recheck_required','recommended_recovery_prompt','summary']}

def validate(decoded: dict[str,Any],case_id: str)->None:
    required={'case_id','overall_decision','stage_decisions','retry_owner',
              'recheck_required','recommended_recovery_prompt','summary'}
    if set(decoded)!=required: raise RuntimeError('Q2 result keys mismatch')
    if decoded['case_id']!=case_id: raise RuntimeError('Q2 case mismatch')
    rows=decoded['stage_decisions']
    if not isinstance(rows,list) or sorted(row.get('stage') for row in rows)!=sorted(STAGES):
        raise RuntimeError('Q2 stage coverage mismatch')
    if any(row.get('status') not in {'PASS','FAIL','UNCERTAIN'} for row in rows):
        raise RuntimeError('Q2 stage status mismatch')
    if decoded['retry_owner']!='none' or decoded['recheck_required'] is not False:
        raise RuntimeError('Q2 must be terminal')
    if decoded['recommended_recovery_prompt']!='':
        raise RuntimeError('Q2 must not recommend another recovery')
    nonpass=[row['stage'] for row in rows if row['status']!='PASS']
    if decoded['overall_decision']=='PASS' and nonpass:
        raise RuntimeError('Q2 PASS contains a non-PASS stage')
    if decoded['overall_decision']=='REJECT_CASE' and not nonpass:
        raise RuntimeError('Q2 rejection has no rejected evidence')
    if decoded['overall_decision'] not in {'PASS','REJECT_CASE'}:
        raise RuntimeError('Q2 nonterminal decision')

def evidence(config: dict[str,Any],panel: Path,manifest: dict[str,Any])->dict[str,dict[str,Any]]:
    if sha(panel)!=manifest.get('panel_sha256'): raise RuntimeError('Q2 panel hash mismatch')
    result={'panel':{'path':str(panel.resolve()),'sha256':sha(panel)}}
    inventories=config.get('inventories')
    if not isinstance(inventories,dict) or set(inventories)!=set(STAGES):
        raise RuntimeError('Q2 inventory roles mismatch')
    for stage in STAGES:
        path=Path(inventories[stage])
        if not path.is_file(): raise FileNotFoundError(str(path))
        packet=json.loads(path.read_text())
        if packet.get('decision')!='foundation_stage_artifact_inventory_closed':
            raise RuntimeError('Q2 inventory not closed:'+stage)
        result[stage]={'path':str(path.resolve()),'sha256':sha(path)}
    return result

def request(config: dict[str,Any],panel: Path,policy: dict[str,Any])->dict[str,Any]:
    prompt=(
      'You are the terminal Q2 jury for one hand-object reconstruction after its only recovery. '
      'Inspect all eight cells and judge each of the seven producers independently. '
      'The selected hand must match the declared image instance and be finite, nondegenerate, '
      'and spatially coherent with its 2D evidence. PASS only when every stage is acceptable. '
      'If any stage is failed or uncertain, return REJECT_CASE. Q2 is terminal: never request '
      'another owner rerun and never suggest a third jury call. Use this project rubric:\n'+
      json.dumps(policy,sort_keys=True,separators=(',',':')))
    mime=mimetypes.guess_type(panel.name)[0] or 'image/png'
    data='data:'+mime+';base64,'+base64.b64encode(panel.read_bytes()).decode('ascii')
    return {'model':config['model'],'reasoning':{'effort':config['reasoning_effort']},
      'input':[{'role':'user','content':[{'type':'input_text','text':prompt},
       {'type':'input_image','image_url':data,'detail':'high'}]}],
      'text':{'format':{'type':'json_schema','name':'tracehoi_q2_terminal_jury',
                       'strict':True,'schema':schema(config['case_id'])}},
      'max_output_tokens':config['max_output_tokens'],'store':False}

def run(config_path: str|Path,panel_path: str|Path,manifest_path: str|Path,
        output_path: str|Path,*,dry_run: bool=False,client: Any=None)->dict[str,Any]:
    config=json.loads(Path(config_path).read_text())
    if config.get('protocol_round')!='Q2': raise RuntimeError('terminal runner requires protocol_round Q2')
    panel=Path(panel_path); manifest=json.loads(Path(manifest_path).read_text())
    owned=evidence(config,panel,manifest)
    policy_path=Path(config['policy']['path'])
    if not policy_path.is_file() or sha(policy_path)!=config['policy']['sha256']:
        raise RuntimeError('Q2 policy mismatch')
    policy=json.loads(policy_path.read_text()); kwargs=request(config,panel,policy)
    public={'model':kwargs['model'],'reasoning':kwargs['reasoning'],
      'image':owned['panel'],'policy':config['policy'],'text':kwargs['text'],
      'max_output_tokens':kwargs['max_output_tokens'],'store':False,'SDK_retries':0}
    if dry_run:
        payload={'schema':'tracehoi.Q2RequestDryRun.v1','case_id':config['case_id'],
          'request':public,'evidence':owned,'api_calls':0,
          'decision':'Q2_nonempty_zero_cost_dry_run_closed'}
        atomic(output_path,payload); return payload
    if client is None:
        from openai import OpenAI
        client=OpenAI(max_retries=0)
    response=client.responses.create(**kwargs)
    if getattr(response,'status',None)!='completed':
        raise RuntimeError('Q2 response not completed:'+str(getattr(response,'status',None)))
    text=getattr(response,'output_text',None)
    if not isinstance(text,str) or not text.strip(): raise RuntimeError('empty Q2 output')
    decoded=json.loads(text); validate(decoded,config['case_id'])
    usage=getattr(response,'usage',None)
    if hasattr(usage,'model_dump'): usage=usage.model_dump(mode='json')
    elif not isinstance(usage,dict): usage={'repr':repr(usage)}
    passed=decoded['overall_decision']=='PASS'
    payload={'schema':'tracehoi.Q2TerminalResult.v1','case_id':config['case_id'],
      'response_id':getattr(response,'id',None),'response_status':'completed',
      'model':getattr(response,'model',config['model']),'usage':usage,
      'decoded':decoded,'evidence':owned,'api_calls':1,'SDK_retries':0,
      'eligible_for_gate_a':passed,'third_jury_call_allowed':False,
      'decision':'Q2_PASS' if passed else 'Q2_REJECT_CASE'}
    atomic(output_path,payload); return payload

def main()->None:
    p=argparse.ArgumentParser(); p.add_argument('--config',required=True)
    p.add_argument('--panel',required=True); p.add_argument('--manifest',required=True)
    p.add_argument('--output',required=True); p.add_argument('--dry-run',action='store_true')
    a=p.parse_args(); got=run(a.config,a.panel,a.manifest,a.output,dry_run=a.dry_run)
    print(json.dumps({'decision':got['decision'],'output':a.output,'api_calls':got['api_calls']},indent=2))
if __name__=='__main__': main()
