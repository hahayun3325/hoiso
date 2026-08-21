from __future__ import annotations
import argparse,csv,hashlib,json,os,sys,time,traceback
from pathlib import Path
from typing import Any

STAGES=['get_hunyuan_input','inpaint','moge','hunyuan','hamer','h2m','mano_registration']
FLOW=['preflight','Q0','prompt_views','foundation_primary','Q1',
      'foundation_recovery_if_requested','Q2_terminal','READY_FOR_GATE_A']

def sha(path: str|Path) -> str:
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def load(path: str|Path) -> dict[str,Any]:
    return json.loads(Path(path).read_text())

def atomic(path: str|Path,payload: dict[str,Any]) -> None:
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_suffix(target.suffix+'.tmp')
    temp.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    os.replace(temp,target)

def replace(value: Any,old: str,new: str) -> Any:
    if isinstance(value,str): return value.replace(old,new)
    if isinstance(value,list): return [replace(item,old,new) for item in value]
    if isinstance(value,dict): return {key:replace(item,old,new) for key,item in value.items()}
    return value

def state(run_root: Path,case_id: str,stage: str,**fields: Any) -> dict[str,Any]:
    path=run_root/'state.json'
    if path.is_file():
        packet=load(path)
        if packet.get('case_id')!=case_id: raise RuntimeError('state case mismatch')
    else:
        packet={'schema':'tracehoi.AutomaticCaseState.v1','case_id':case_id,
                'transitions':[],'created_unix':time.time()}
    packet['stage']=stage; packet['updated_unix']=time.time(); packet.update(fields)
    packet['transitions'].append({'stage':stage,'unix':packet['updated_unix']})
    atomic(path,packet)
    with (run_root/'events.jsonl').open('a') as stream:
        stream.write(json.dumps(packet['transitions'][-1],sort_keys=True)+'\n')
    return packet

def checked_image(config: dict[str,Any]) -> Path:
    image=Path(config['image']['path'])
    if not image.is_file(): raise FileNotFoundError(str(image))
    if sha(image)!=config['image']['sha256']: raise RuntimeError('accepted image hash mismatch')
    return image

def values(packet: dict[str,Any],family: str) -> dict[str,Any]:
    keys=('foundation_primary','primary_values') if family=='primary' \
         else ('foundation_recovery','recovery_values')
    for key in keys:
        value=packet.get(key)
        if isinstance(value,dict): return value
    raise RuntimeError('missing Q0 '+family+' foundation values')

def encode(value: Any) -> str:
    if isinstance(value,str) and value.strip(): return value.strip()
    if isinstance(value,list) and value \
       and all(isinstance(item,str) and item.strip() for item in value):
        return ', '.join(item.strip() for item in value)
    raise RuntimeError('invalid short-keyword prompt value')

def resolve_hand_instance(packet: dict[str,Any]) -> dict[str,Any]:
    raw=str((packet.get('gate_b') or {}).get('hand_instance',''))
    allowed={'upper_image_hand','lower_image_hand','single_hand','ambiguous'}
    if raw not in allowed:
        raise RuntimeError('invalid or missing Q0 gate_b.hand_instance:'+repr(raw))
    active=str((packet.get('gate_d0') or {}).get('active_hand','')).strip().lower()
    positional=[]
    if 'upper' in active: positional.append('upper_image_hand')
    if 'lower' in active: positional.append('lower_image_hand')
    if raw=='ambiguous':
        if len(positional)!=1:
            raise RuntimeError('ambiguous Gate-B hand has no unique Gate-D0 positional owner:'+repr(active))
        resolved=positional[0]
        owner='gate_d0.active_hand'
    else:
        resolved=raw
        owner='gate_b.hand_instance'
        if raw in {'upper_image_hand','lower_image_hand'} and positional and positional!=[raw]:
            raise RuntimeError('Gate-B/Gate-D0 hand owner conflict:'+repr((raw,active)))
    return {'schema':'tracehoi.HandInstanceResolution.v1',
      'gate_b_hand_instance':raw,'gate_d0_active_hand':active,
      'resolved_hand_instance':resolved,'resolution_owner':owner,
      'decision':'hand_instance_resolution_closed'}

def validate_q0_packet(path: str|Path) -> Path:
    packet=load(path)
    for family in ('primary','recovery'):
        selected=values(packet,family)
        for key in ('category_compatibility','object_segmentation','flux_inpainting'):
            encode(selected.get(key))
    return Path(path)

def validate_jury_result(packet: dict[str,Any],round_name: str) -> dict[str,Any]:
    verdict,retry_owner=decision(packet)
    if round_name=='Q2':
        if packet.get('schema')!='tracehoi.Q2TerminalResult.v1':
            raise RuntimeError('Q2 terminal schema mismatch')
        if verdict not in {'PASS','REJECT_CASE'}:
            raise RuntimeError('Q2 must be terminal:'+verdict)
        if packet.get('eligible_for_gate_a') is not (verdict=='PASS'):
            raise RuntimeError('Q2 eligibility mismatch')
        if packet.get('third_jury_call_allowed') is not False:
            raise RuntimeError('Q2 third-call invariant')
    else:
        if verdict not in {'PASS','RETRY_ONE_OWNER','REJECT_CASE'}:
            raise RuntimeError(round_name+' invalid verdict:'+verdict)
        if verdict=='RETRY_ONE_OWNER' and not retry_owner:
            raise RuntimeError(round_name+' retry owner absent')
    return packet

def prompt_views(packet_path: str|Path,config: dict[str,Any],family: str,
                 root: Path) -> dict[str,str]:
    packet=load(packet_path); selected=values(packet,family); image=checked_image(config)
    category=encode(selected['category_compatibility'])
    object_prompt=encode(selected['object_segmentation'])
    scalar=config['prompt_policy'].get('object_segmentation_single_label')
    if scalar:
        object_prompt=encode(scalar)
    elif family=='recovery' and config['prompt_policy'].get('recovery_object_single_label'):
        object_prompt=config['prompt_policy']['recovery_object_single_label']
    flux=encode(selected['flux_inpainting'])
    rows={'category':category,'object':object_prompt,'flux':flux}; paths={}
    for role,value in rows.items():
        path=root/f'{role}.csv'; path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix('.csv.tmp')
        with temp.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=['image_id','image_path','response'])
            writer.writeheader(); writer.writerow({'image_id':config['case_id'],
              'image_path':str(image),'response':value})
        os.replace(temp,path); paths[role]=str(path)
    receipt={'schema':'tracehoi.AutomaticPromptViews.v1','family':family,
      'views':{key:{'path':path,'sha256':sha(path)} for key,path in paths.items()},
      'hand_segmentation_prompt':config['prompt_policy']['hand_segmentation'],
      'decision':'automatic_prompt_views_closed'}
    atomic(root/'prompt_views.json',receipt); return paths

def runtime_config(template: str|Path,old_root: str,new_root: str,image: Path,
                   prompts: dict[str,str],output: Path,
                   hand_instance: str='closest_to_object') -> None:
    text=Path(template).read_text().replace(old_root,new_root)
    updates={'IMAGE_PATH':str(image),'BASE_DIR':new_root,
      'GEMINI_RESPONSES':prompts['category'],
      'OBJECT_PROMPT_CSV':prompts['object'],'FLUX_PROMPT_CSV':prompts['flux'],
      'HAND_INSTANCE':hand_instance}
    lines=[]; seen=set()
    for line in text.splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key=line.split('=',1)[0]
            if key in updates: line=key+'='+updates[key]; seen.add(key)
        lines.append(line)
    missing=set(updates)-seen
    for key in sorted(missing & {'HAND_INSTANCE'}):
        lines.append(key+'='+updates[key])
    remaining=missing-{'HAND_INSTANCE'}
    if remaining: raise RuntimeError('runtime template missing keys:'+repr(sorted(remaining)))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text('\n'.join(lines)+'\n')

def run_q0(config: dict[str,Any],run_root: Path,model: str,
           reuse: str|None) -> Path:
    if reuse:
        path=Path(reuse)
        if not path.is_file(): raise FileNotFoundError(str(path))
        return validate_q0_packet(path)
    from openai import OpenAI
    from foho.automation import combined_q0,combined_q0_runner
    roots={'${PROJECT_ROOT}':config['project_root'],'${PHASE0_ROOT}':config['phase0_root'],
           '${CASE_ROOT}':config['case_root']}
    contract=combined_q0.load_contract(config['q0']['config'],roots)
    if contract.model!=model: raise RuntimeError(f'Q0 model mismatch:{contract.model}:{model}')
    output=run_root/'q0'; claim=output/'call_claim.json'
    if (output/'combined_Q0_semantic_packet.json').is_file():
        return output/'combined_Q0_semantic_packet.json'
    output.mkdir(parents=True,exist_ok=True)
    with claim.open('x') as stream:
        stream.write(json.dumps({'one_call_only':True,'created_unix':time.time()})+'\n')
    client=OpenAI(max_retries=0)
    combined_q0_runner.execute(client,contract,output,
      max_output_tokens=config['q0']['max_output_tokens'],transport_authorized=True)
    packet=output/'combined_Q0_semantic_packet.json'
    if not packet.is_file(): raise RuntimeError('Q0 packet absent after returned call')
    return validate_q0_packet(packet)

def run_foundation(config: dict[str,Any],run_root: Path,packet: Path,
                   family: str,gpu: str) -> Path:
    owner=run_root/'foundation'/family
    result_path=owner/'controller'/'controller_result.json'
    if result_path.is_file() \
       and load(result_path).get('decision')=='foundation_process_controller_closed':
        return owner/'outputs'
    prompts=prompt_views(packet,config,family,run_root/'config'/family/'prompts')
    output_root=owner/'outputs'; env_path=run_root/'config'/family/'foundation.env'
    hand_resolution=resolve_hand_instance(load(packet))
    atomic(run_root/'receipts'/f'{family}_hand_instance_resolution.json',hand_resolution)
    runtime_config(config['foundation']['runtime_template'],
      config['foundation']['template_root'],str(output_root),checked_image(config),prompts,
      env_path,hand_instance=hand_resolution['resolved_hand_instance'])
    raw_manifest=run_root/'config'/family/'manifest_unbound.json'
    bound_manifest=run_root/'config'/family/'manifest_GPU.json'
    bind_receipt=run_root/'receipts'/f'{family}_GPU_binding.json'
    from foho.automation.foundation_manifest import build
    from foho.automation.foundation_gpu_bind import bind
    from foho.automation.foundation_process_controller import run_manifest
    manifest=build(env_path,raw_manifest)
    names=[row['name'] for row in manifest.get('stages',[])]
    if names!=STAGES: raise RuntimeError('foundation stage order mismatch:'+repr(names))
    bind_receipt.parent.mkdir(parents=True,exist_ok=True)
    binding=bind(raw_manifest,bound_manifest,bind_receipt,names,gpu)
    if binding.get('decision')!='foundation_manifest_GPU_binding_closed':
        raise RuntimeError('GPU binding did not close:'+repr(binding.get('errors')))
    os.environ['CUDA_VISIBLE_DEVICES']=gpu
    result=run_manifest(bound_manifest,owner/'controller',dry_run=False)
    if result.get('decision')!='foundation_process_controller_closed':
        raise RuntimeError('foundation controller:'+str(result.get('decision')))
    return output_root

def jury_config(config: dict[str,Any],foundation_root: Path,model: str,
                round_name: str,run_root: Path) -> Path:
    template=load(config['jury']['config_template'])
    packet=replace(template,config['jury']['template_foundation_root'],str(foundation_root))
    packet['model']=model; packet['reasoning_effort']=config['jury']['reasoning_effort']
    packet['protocol_round']=round_name
    path=run_root/'config'/f'{round_name}.json'; atomic(path,packet); return path

def run_jury(config: dict[str,Any],foundation_root: Path,model: str,
             round_name: str,run_root: Path) -> dict[str,Any]:
    from foho.automation.q1_evidence_panel import build
    if round_name=='Q2':
        from foho.automation.q2_terminal_runner import run
    else:
        from foho.automation.q1_responses_runner import run
    panel=run_root/'panels'/f'{round_name}.png'
    manifest=run_root/'panels'/f'{round_name}.json'
    result_path=run_root/'jury'/f'{round_name}_result.json'
    if result_path.is_file(): return validate_jury_result(load(result_path),round_name)
    config_path=jury_config(config,foundation_root,model,round_name,run_root)
    build(config_path,panel,manifest)
    dry=run_root/'jury'/f'{round_name}_dry_run.json'
    rehearsed=run(config_path,panel,manifest,dry,dry_run=True)
    expected=round_name+'_nonempty_zero_cost_dry_run_closed'
    if rehearsed.get('decision')!=expected:
        raise RuntimeError(round_name+' dry run did not close:'+str(rehearsed.get('decision')))
    claim=run_root/'jury'/f'{round_name}_call_claim.json'
    claim.parent.mkdir(parents=True,exist_ok=True)
    with claim.open('x') as stream:
        stream.write(json.dumps({'round':round_name,'one_call_only':True,
          'created_unix':time.time()})+'\n')
    return validate_jury_result(
      run(config_path,panel,manifest,result_path,dry_run=False),round_name)

def decision(result: dict[str,Any]) -> tuple[str,str]:
    decoded=result.get('decoded') or {}
    return str(decoded.get('overall_decision')),str(decoded.get('retry_owner'))

def run_case(args: argparse.Namespace) -> dict[str,Any]:
    config=load(args.config); root=Path(args.run_root)
    if root.exists() and any(root.iterdir()) and not args.resume:
        raise RuntimeError('run root is nonempty; pass --resume to reuse audited state')
    root.mkdir(parents=True,exist_ok=True); checked_image(config)
    state(root,config['case_id'],'PREFLIGHT_CLOSED',gpu=args.gpu)
    q0=run_q0(config,root,args.semantic_model,args.reuse_q0_packet)
    state(root,config['case_id'],'Q0_CLOSED',Q0_packet=str(q0),Q0_sha256=sha(q0))
    if args.reuse_q1_result:
        q1=validate_jury_result(load(args.reuse_q1_result),'Q1')
        state(root,config['case_id'],'Q1_REUSED',Q1_result=args.reuse_q1_result,
              Q1_sha256=sha(args.reuse_q1_result))
    else:
        primary=run_foundation(config,root,q0,'primary',args.gpu)
        state(root,config['case_id'],'PRIMARY_FOUNDATION_CLOSED',root=str(primary))
        q1=run_jury(config,primary,args.jury_model,'Q1',root)
        state(root,config['case_id'],'Q1_CLOSED',Q1_decision=decision(q1)[0])
    q1_decision,retry_owner=decision(q1)
    if q1_decision=='PASS':
        return state(root,config['case_id'],'READY_FOR_GATE_A',jury_round='Q1')
    if q1_decision=='REJECT_CASE':
        return state(root,config['case_id'],'TERMINAL_REJECTED',jury_round='Q1')
    if q1_decision!='RETRY_ONE_OWNER':
        raise RuntimeError('invalid Q1 decision:'+q1_decision)
    if getattr(args,'stop_after_q1',False):
        return state(root,config['case_id'],'Q1_RECOVERY_PENDING',
                     Q1_decision=q1_decision,Q1_retry_owner=retry_owner,
                     recovery_started=False)
    if args.max_recovery_rounds!=1:
        raise RuntimeError('exactly one recovery round is supported')
    supported=config['recovery']['supported_retry_owners']
    if retry_owner not in supported:
        raise RuntimeError('retry owner not yet connected:'+retry_owner)
    recovery=run_foundation(config,root,q0,'recovery',args.gpu)
    state(root,config['case_id'],'RECOVERY_FOUNDATION_CLOSED',retry_owner=retry_owner,
          root=str(recovery))
    q2=run_jury(config,recovery,args.jury_model,'Q2',root)
    q2_decision,q2_owner=decision(q2)
    if q2_decision=='PASS':
        return state(root,config['case_id'],'READY_FOR_GATE_A',jury_round='Q2')
    return state(root,config['case_id'],'TERMINAL_REJECTED_AFTER_Q2',
                 Q2_decision=q2_decision,Q2_retry_owner=q2_owner,
                 third_jury_call_allowed=False)

def parser() -> argparse.ArgumentParser:
    top=argparse.ArgumentParser(prog='tracehoi-auto')
    sub=top.add_subparsers(dest='command',required=True)
    plan=sub.add_parser('plan'); plan.add_argument('--config',required=True)
    status=sub.add_parser('status'); status.add_argument('--run-root',required=True)
    run=sub.add_parser('run'); run.add_argument('--config',required=True)
    run.add_argument('--run-root',required=True); run.add_argument('--gpu',required=True)
    run.add_argument('--semantic-model',required=True); run.add_argument('--jury-model',required=True)
    run.add_argument('--max-recovery-rounds',type=int,default=1)
    run.add_argument('--reuse-q0-packet'); run.add_argument('--reuse-q1-result')
    run.add_argument('--resume',action='store_true')
    run.add_argument('--stop-after-q1',action='store_true')
    return top

def main() -> int:
    args=parser().parse_args()
    if args.command=='plan':
        print(json.dumps({'decision':'automatic_case_plan_closed','flow':FLOW,
          'config':args.config,'api_calls':0,'cuda_started':False},indent=2)); return 0
    if args.command=='status':
        path=Path(args.run_root)/'state.json'
        print(path.read_text() if path.is_file()
              else json.dumps({'stage':'NOT_STARTED'},indent=2)); return 0
    try:
        print(json.dumps(run_case(args),indent=2))
        return 0
    except Exception as exc:
        root=Path(args.run_root); root.mkdir(parents=True,exist_ok=True)
        payload=state(root,load(args.config).get('case_id','unknown'),'BLOCKED',
          error_type=type(exc).__name__,error_message=str(exc),
          traceback=traceback.format_exc())
        print(json.dumps(payload,indent=2))
        return 1

if __name__=='__main__': raise SystemExit(main())
