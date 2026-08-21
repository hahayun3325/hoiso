from __future__ import annotations
import argparse, base64, hashlib, json, mimetypes, os
from pathlib import Path
from typing import Any

STAGES=['get_hunyuan_input','inpaint','moge','hunyuan','hamer','h2m','mano_registration']

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def atomic(path: Path, payload: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True); temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n'); os.replace(temp,path)

def schema(case_id: str) -> dict[str,Any]:
    stage={'type':'object','additionalProperties':False,
      'properties':{'stage':{'type':'string','enum':STAGES},
        'status':{'type':'string','enum':['PASS','FAIL','UNCERTAIN']},
        'confidence':{'type':'number','minimum':0,'maximum':1},'evidence':{'type':'string'}},
      'required':['stage','status','confidence','evidence']}
    return {'type':'object','additionalProperties':False,
      'properties':{'case_id':{'type':'string','enum':[case_id]},
        'overall_decision':{'type':'string','enum':['PASS','RETRY_ONE_OWNER','REJECT_CASE']},
        'stage_decisions':{'type':'array','items':stage,'minItems':7,'maxItems':7},
        'retry_owner':{'type':'string','enum':['none']+STAGES},
        'recheck_required':{'type':'boolean'},'recommended_recovery_prompt':{'type':'string'},
        'summary':{'type':'string'}},
      'required':['case_id','overall_decision','stage_decisions','retry_owner',
        'recheck_required','recommended_recovery_prompt','summary']}

def validate(packet: dict[str,Any],case_id: str) -> None:
    required={'case_id','overall_decision','stage_decisions','retry_owner','recheck_required',
              'recommended_recovery_prompt','summary'}
    if set(packet)!=required: raise RuntimeError('Q1 result keys mismatch')
    if packet['case_id']!=case_id: raise RuntimeError('Q1 case_id mismatch')
    rows=packet['stage_decisions']
    if not isinstance(rows,list) or sorted(row.get('stage') for row in rows)!=sorted(STAGES):
        raise RuntimeError('Q1 stage coverage mismatch')
    if any(row.get('status') not in {'PASS','FAIL','UNCERTAIN'} for row in rows):
        raise RuntimeError('Q1 stage status mismatch')
    decision=packet['overall_decision']; owner=packet['retry_owner']; recheck=packet['recheck_required']
    failed=[row['stage'] for row in rows if row['status']=='FAIL']
    not_pass=[row['stage'] for row in rows if row['status']!='PASS']
    if decision=='PASS' and (owner!='none' or recheck or not_pass): raise RuntimeError('inconsistent PASS')
    if decision=='RETRY_ONE_OWNER' and (owner not in STAGES or failed!=[owner]
                                        or not_pass!=[owner] or not recheck):
        raise RuntimeError('inconsistent one-owner retry')
    if decision=='REJECT_CASE' and owner!='none': raise RuntimeError('REJECT_CASE must not retry')

def request(config: dict[str,Any],panel: Path,policy: dict[str,Any]) -> dict[str,Any]:
    prompt=(
      'You are the automatic Q1 jury for a single-image hand-object reconstruction. '
      'Inspect all eight labeled cells. Judge each fresh producer independently. '
      'Stage contract: MoGe is joint observation-space scene/depth and may contain exactly '
      'the selected hand plus object; do not reject it merely for that hand. Hunyuan is the '
      'object-only geometry branch and must not contain hand or arm geometry. '
      'Masks must select the named semantic role without obvious leakage; inpainting must be '
      'locally plausible and preserve visible evidence; MoGe must be coherent; Hunyuan and HaMeR '
      'must have plausible nondegenerate geometry; H2M and MANO outputs must be present and coherent. '
      'Do not compare with a historical final alignment and do not reward a later stage for hiding '
      'an earlier defect. PASS only if all seven producers are acceptable. RETRY_ONE_OWNER only when '
      'exactly one producer is visibly defective and one bounded rerun could repair it. Otherwise '
      'REJECT_CASE. Treat the following policy JSON as the owned project rubric:\n'+
      json.dumps(policy,sort_keys=True,separators=(',',':')))
    mime=mimetypes.guess_type(panel.name)[0] or 'image/png'
    data='data:'+mime+';base64,'+base64.b64encode(panel.read_bytes()).decode('ascii')
    return {'model':config['model'],'reasoning':{'effort':config['reasoning_effort']},
      'input':[{'role':'user','content':[{'type':'input_text','text':prompt},
        {'type':'input_image','image_url':data,'detail':'high'}]}],
      'text':{'format':{'type':'json_schema','name':'tracehoi_q1_jury','strict':True,
                       'schema':schema(config['case_id'])}},
      'max_output_tokens':config['max_output_tokens'],'store':False}

def run(config_path: str|Path,panel_path: str|Path,manifest_path: str|Path,
        output_path: str|Path,*,dry_run: bool=False,client: Any=None) -> dict[str,Any]:
    config=json.loads(Path(config_path).read_text()); panel=Path(panel_path)
    manifest=json.loads(Path(manifest_path).read_text()); policy_path=Path(config['policy']['path'])
    if sha(panel)!=manifest.get('panel_sha256'): raise RuntimeError('panel hash mismatch')
    if sha(policy_path)!=config['policy']['sha256']: raise RuntimeError('policy hash mismatch')
    policy=json.loads(policy_path.read_text()); kwargs=request(config,panel,policy)
    public_request={'model':kwargs['model'],'reasoning':kwargs['reasoning'],
      'image':{'path':str(panel.resolve()),'sha256':sha(panel),'detail':'high'},
      'policy':config['policy'],'text':kwargs['text'],'max_output_tokens':kwargs['max_output_tokens'],
      'store':False,'SDK_retries':0}
    output=Path(output_path)
    if dry_run:
        payload={'schema':'tracehoi.Q1RequestDryRun.v1','case_id':config['case_id'],
          'request':public_request,'api_calls':0,'decision':'Q1_nonempty_zero_cost_dry_run_closed'}
        atomic(output,payload); return payload
    if client is None:
        from openai import OpenAI
        client=OpenAI(max_retries=0)
    response=client.responses.create(**kwargs)
    status=getattr(response,'status',None)
    if status!='completed': raise RuntimeError('Q1 response not completed: '+str(status))
    text=getattr(response,'output_text',None)
    if not isinstance(text,str) or not text.strip(): raise RuntimeError('empty Q1 output_text')
    decoded=json.loads(text); validate(decoded,config['case_id'])
    usage=getattr(response,'usage',None)
    if hasattr(usage,'model_dump'): usage=usage.model_dump(mode='json')
    elif not isinstance(usage,dict): usage={'repr':repr(usage)}
    payload={'schema':'tracehoi.Q1LiveResult.v1','case_id':config['case_id'],
      'response_id':getattr(response,'id',None),'response_status':status,
      'model':getattr(response,'model',config['model']),'usage':usage,
      'panel':public_request['image'],'policy':config['policy'],'decoded':decoded,
      'api_calls':1,'SDK_retries':0,'decision':'Q1_'+decoded['overall_decision']}
    atomic(output,payload); return payload

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--config',required=True)
    parser.add_argument('--panel',required=True); parser.add_argument('--manifest',required=True)
    parser.add_argument('--output',required=True); parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args(); result=run(args.config,args.panel,args.manifest,args.output,dry_run=args.dry_run)
    print(json.dumps({'decision':result['decision'],'output':args.output,'api_calls':result['api_calls']},indent=2))
if __name__=='__main__': main()
