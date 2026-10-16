from __future__ import annotations
import argparse,json
from pathlib import Path
from foho.automation.foundation_terminal_contract import sha,validate_foundation_terminal
from foho.automation import frame_i_gate_c_adapter,gate_a_adapter
from foho.automation.pilot_dag import RestartableCaseDAG

STAGES=("gate_a","frame_i","gate_c","d0","h0","h1","o0","j0","f0","final_export","evaluation")
def _control_path(path):
    path=Path(path)
    if not path.is_absolute() or any(p.is_symlink() for p in (path,*path.parents)):
        raise RuntimeError('unsafe control path: '+str(path))
    return path

def _control_json(path,expected_sha=''):
    path=_control_path(path)
    if not path.is_file() or path.stat().st_size>2*1024**2:
        raise RuntimeError('missing or oversized control file: '+str(path))
    data=path.read_bytes()
    import hashlib
    if expected_sha!='':
        if not isinstance(expected_sha,str) or len(expected_sha)!=64 or any(c not in '0123456789abcdef' for c in expected_sha):
            raise RuntimeError('invalid control hash')
        if hashlib.sha256(data).hexdigest()!=expected_sha:
            raise RuntimeError('control hash mismatch: '+str(path))
    def pairs(rows):
        packet={}
        for key,value in rows:
            if key in packet: raise RuntimeError('duplicate control JSON key')
            packet[key]=value
        return packet
    def nonfinite(value): raise RuntimeError('nonfinite control JSON')
    packet=json.loads(data,object_pairs_hook=pairs,parse_constant=nonfinite)
    if not isinstance(packet,dict): raise RuntimeError('control JSON must be an object')
    return packet

def _resume_state(config,run_root):
    root=_control_path(run_root); state=_control_json(root/'state.json')
    index=state.get('next_index'); history=state.get('history')
    if (state.get('schema')!='tracehoi.AutomaticPilotState.v1'
        or state.get('case_id')!=config['case_id'] or state.get('stage_order')!=list(STAGES)
        or type(index) is not int or not 0<=index<=len(STAGES)
        or not isinstance(history,list) or len(history)!=index
        or any(not isinstance(row,dict) for row in history)
        or [row.get('stage') for row in history]!=list(STAGES[:index])
        or state.get('status')!=('complete' if index==len(STAGES) else 'ready')):
        raise RuntimeError('resume state boundary is inconsistent or failed')
    return state

def resume_guarded(config_path,run_root):
    # Observation only: never instantiate a DAG or choose a mock producer.
    config=load_config(config_path); state=_resume_state(config,run_root)
    index=state['next_index']
    return {'schema':'tracehoi.PostQ2ResumeBlocked.v1','case_id':config['case_id'],
      'decision':'post_Q2_resume_requires_explicit_stage_adapter',
      'controller_status':state['status'],'next_index':index,
      'next_stage':STAGES[index] if index<len(STAGES) else None,
      'eligible_for_execution':False,'State_edits':0,'stage_calls':0,
      'reason':'Generic resume has no real later-stage dispatch. Use a supported explicit real-stage adapter; mock mode is restricted to empty or verified mock-only runs.'}

def _assert_mock_run(config,run_root):
    root=_control_path(run_root)
    if not root.exists(): return
    if not root.is_dir(): raise RuntimeError('mock run root is not a directory')
    if not (root/'state.json').exists():
        if any(root.iterdir()): raise RuntimeError('nonempty unclassified run cannot become mock')
        return
    state=_resume_state(config,root); previous=None
    for index,entry in enumerate(state['history']):
        stage=STAGES[index]
        expected_receipt=root/'receipts'/('%02d_%s.json'%(index,stage))
        if entry.get('receipt_path')!=str(expected_receipt) or set(entry)!={'stage','receipt_path','receipt_sha256'}:
            raise RuntimeError('real or unknown history cannot resume as mock')
        receipt=_control_json(expected_receipt,entry['receipt_sha256'])
        if (receipt.get('schema')!='tracehoi.StageHandoffReceipt.v1'
            or receipt.get('case_id')!=config['case_id'] or receipt.get('index')!=index
            or receipt.get('stage')!=stage or receipt.get('decision')!='stage_handoff_closed'):
            raise RuntimeError('not a mock-compatible receipt')
        inputs=receipt.get('inputs'); outputs=receipt.get('outputs')
        if not isinstance(inputs,dict) or not inputs or set(outputs or {})!={stage}:
            raise RuntimeError('mock receipt owner set mismatch')
        if previous is not None and inputs!=previous: raise RuntimeError('mock receipt chain mismatch')
        expected_output=root/('%02d_%s'%(index,stage))/(stage+'_mock.json')
        if outputs[stage].get('path')!=str(expected_output): raise RuntimeError('unexpected mock output path')
        artifact=_control_json(expected_output,outputs[stage]['sha256'])
        if (artifact.get('schema')!='tracehoi.PostQ2MockArtifact.v1'
            or artifact.get('stage')!=stage or artifact.get('inputs')!=inputs):
            raise RuntimeError('real or unknown artifact cannot resume as mock')
        for record in inputs.values(): _control_json(record['path'],record['sha256'])
        previous=outputs
    if previous is not None and state.get('last_outputs')!=previous:
        raise RuntimeError('mock last-output binding mismatch')
    if not state['history'] and set(p.name for p in root.iterdir())!={'state.json'}:
        raise RuntimeError('unclassified zero-stage run contents')
    if not state['history']:
        records=state.get('last_outputs',{})
        if set(records)!={'foundation_terminal'}: raise RuntimeError('zero-stage foundation binding mismatch')
        rec=records['foundation_terminal']; _control_json(rec['path'],rec['sha256'])

_J0_REVIEW_EVIDENCE_SHA256='7a6193e471df1577e67b1815e69e0db507ae4e1e9e568976c77541bd26a4f3c2'
_J0_REVIEW_IMPLEMENTATION='f32bb92b0d40554b27a98b3a94601872cfd1a7cb915f97caf401d80e6c049e9e'
_J0_REVIEW_PAYLOADS=['constraint_disposition.json', 'j0_review_terminal.json', 'j0_trial_review_dispatch_candidate.py', 'measurement_evidence.json', 'plan.json', 'policy_reference.py', 'publication_reference.py', 'resume_boundary_reference.py', 'review_commit.json', 'review_dispatch_tests.py', 'run_report.json', 'source_bindings.json', 'test_report.json', 'trial_disposition.json', 'trial_events_reference.json', 'trial_result_reference.json']
_J0_REVIEW_PAYLOADS=set(_J0_REVIEW_PAYLOADS)
def _j0_review_require(ok,message):
    if not ok:raise RuntimeError(message)

def _j0_review_read(path,pin=None):
    import hashlib
    p=_control_path(path)
    _j0_review_require(p.is_file(),'J0_review_missing_file:'+str(p))
    a=p.stat();_j0_review_require(a.st_size<=16*1024**2,'J0_review_file_too_large')
    b=p.read_bytes();z=p.stat()
    _j0_review_require((a.st_ino,a.st_size,a.st_mtime_ns)==(z.st_ino,z.st_size,z.st_mtime_ns),'J0_source_changed_during_read')
    h=hashlib.sha256(b).hexdigest();_j0_review_require(pin is None or h==pin,'J0_review_hash_mismatch:'+str(p))
    return b,{'path':str(p),'bytes':len(b),'sha256':h}

def _j0_review_unpack(data):
    import hashlib,io,zipfile
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names=z.namelist();mn=[n for n in names if n.endswith('/transfer_manifest.json')]
        _j0_review_require(len(mn)==1 and len(names)==len(set(names)) and sum(v.file_size for v in z.infolist())<=2*1024**2,'J0_review_ZIP_inventory')
        _j0_review_require(z.testzip() is None,'J0_review_ZIP_CRC')
        prefix=mn[0].removesuffix('transfer_manifest.json');manifest=json.loads(z.read(mn[0]))['files']
        _j0_review_require(set(names)=={prefix+k for k in manifest}|{mn[0]},'J0_review_ZIP_members')
        files={}
        for n,r in manifest.items():
            _j0_review_require(Path(n).name==n,'J0_review_ZIP_path')
            b=z.read(prefix+n);_j0_review_require(len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],'J0_review_payload_changed:'+n);files[n]=b
    return files

_J0_RUNNER_TRANSITION='/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/tracehoi_autopipeline_0_0_5_20260831T131948Z/diagnostics/step_0ce_j0_runner_installation_v1/runner_source_transition.json'
def _j0_check_runner_source(record):
    """One explicit version transition; historical review provenance stays intact."""
    _, current = _j0_review_read(record['path'])
    if current == record:
        return None
    transition_path = _control_path(_J0_RUNNER_TRANSITION)
    raw, binding = _j0_review_read(transition_path)
    t = _control_json(transition_path, binding['sha256'])
    expected_keys = {'schema','case_id','source_key','previous','replacement','backup_path','versioned_path','evidence_sha256','scope'}
    _j0_review_require(set(t) == expected_keys, 'J0_runner_transition_fields')
    _j0_review_require(t['schema'] == 'tracehoi.RunnerSourceTransition.v1' and t['case_id'] == 'alapuse02v3n60'
        and t['source_key'] == 'post_q2_runner' and t['previous'] == record
        and t['replacement'] == current and current['path'] == record['path']
        and t['evidence_sha256'] == _J0_REVIEW_EVIDENCE_SHA256
        and t['scope'] == 'runner control code only; no scientific source or acceptance change', 'J0_runner_transition_binding')
    _j0_review_require(t['backup_path'] == str(transition_path.parent/'post_q2_runner_before.py')
        and t['versioned_path'] == str(transition_path.parent/'post_q2_runner_installed.py'), 'J0_runner_transition_paths')
    old, old_binding = _j0_review_read(t['backup_path'], record['sha256'])
    new, new_binding = _j0_review_read(t['versioned_path'], current['sha256'])
    _j0_review_require(len(old) == record['bytes'] and len(new) == current['bytes'], 'J0_runner_transition_sizes')
    executing = _control_path(__file__)
    _j0_review_require(str(executing) in (record['path'], t['versioned_path']), 'J0_unrecorded_executing_runner')
    _j0_review_require(_j0_review_read(executing, current['sha256'])[0] == new, 'J0_executing_runner_changed')
    return {'transition_binding': binding, 'previous': record, 'replacement': current,
        'historical_review_sources_preserved': True}


def run_j0_review(mode,config_path,run_root,evidence_path,review_root):
    """Explicit saved-review entry. Never call make_dag, a producer or a fitter."""
    import hashlib
    _j0_review_require(mode in ('j0-review','j0-review-resume'),'J0_explicit_review_mode_required')
    evidence_path=_control_path(evidence_path);review_root=_control_path(review_root);live=_control_path(run_root)
    data,evidence_binding=_j0_review_read(evidence_path,_J0_REVIEW_EVIDENCE_SHA256)
    package=_j0_review_unpack(data)
    _j0_review_require(set(package)==_J0_REVIEW_PAYLOADS,'J0_review_exact_inventory')
    report=json.loads(package['run_report.json']);sources=json.loads(package['source_bindings.json'])
    _j0_review_require(report['decision']=='J0_rejected_trial_review_dispatch_verified_no_promotion_review_required' and report['errors']==[] and report['implementation_sha256']==_J0_REVIEW_IMPLEMENTATION,'J0_0CC_completion_required')
    _j0_review_require(report['source_bindings']==sources and report['tests']==json.loads(package['test_report.json']) and report['tests']['passed']==55,'J0_0CC_report_changed')
    _j0_review_require(_control_path(config_path)==Path(sources['post_q2_config']['path']) and live/'state.json'==Path(sources['state']['path']),'J0_wrong_config_or_run')
    # Keep integration output within this case's diagnostics, outside accepted State.
    diagnostic_root=Path(sources['cb_zip']['path']).parents[1]
    _j0_review_require(diagnostic_root in review_root.parents,'J0_review_output_outside_case_diagnostics')
    transition=[]
    def recheck():
        _j0_review_require(_j0_review_read(evidence_path,_J0_REVIEW_EVIDENCE_SHA256)[1]==evidence_binding,'J0_review_evidence_changed')
        current_transition=_j0_check_runner_source(sources['post_q2_runner'])
        if transition:_j0_review_require(transition[0]==current_transition,'J0_runner_transition_changed_during_review')
        else:transition.append(current_transition)
        for k,r in sources.items():
            if k!='post_q2_runner':_j0_review_require(_j0_review_read(r['path'],r['sha256'])[1]==r,'J0_review_source_changed:'+k)
    recheck()
    modules={}
    for key,name in [('policy','policy_reference.py'),('publication','publication_reference.py'),('dispatch','j0_trial_review_dispatch_candidate.py')]:
        # Code is executed only after the entire archive matches the reviewed SHA256.
        modules[key]={'__name__':'verified_'+key};exec(compile(package[name],name,'exec'),modules[key])
    pm=modules['policy'];adapter=modules['dispatch'];publication=modules['publication']
    boundary=resume_guarded(config_path,live)
    evidence=json.loads(package['measurement_evidence.json']);constraints=json.loads(package['constraint_disposition.json'])
    state=_control_json(sources['state']['path'],sources['state']['sha256'])
    compiled=_control_json(sources['compiled']['path'],sources['compiled']['sha256'])
    baseline=evidence['identity_reference'];policy=pm['make_policy'](baseline,compiled)
    _j0_review_require(compiled==constraints['compiled_D0_preserved'] and policy==constraints['proposal_policy_preserved'],'J0_current_policy_changed')
    files=adapter['prepare'](state,compiled,baseline,policy,json.loads(package['trial_result_reference.json']),
      json.loads(package['trial_events_reference.json']),sources,boundary,pm['score'])
    _j0_review_require(all(v==package[k] for k,v in files.items()),'J0_review_reconstruction_changed')
    expected_commit={'schema':'tracehoi.CommittedJ0ReviewEvidence.v1','files':{k:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for k,v in files.items()},'stage_accepted':False,'State_edits':0}
    _j0_review_require(publication['encoded'](expected_commit)==package['review_commit.json'],'J0_0CC_commit_changed')
    disposition=evidence['trial_disposition']
    _j0_review_require(disposition==report['disposition']==json.loads(package['trial_disposition.json']) and disposition['outcome']=='no_qualifying_proposal','J0_trial_disposition_changed')
    out=adapter['dispatch'](mode,review_root,live,files,recheck,publication)
    recheck()
    return {'schema':'tracehoi.PostQ2J0ReviewDispatch.v1','case_id':state['case_id'],'mode':mode,
      **out,'review_root':str(review_root),'evidence_binding':evidence_binding,'runner_source_transition':transition[0],
      'execution_scope':'saved completed J0 trial review; no live stage acceptance or automatic continuation',
      'geometry_evaluations':0,'model_calls':0,'optimizer_steps':0,'live_installations':0}

def load_config(path):
    packet=json.loads(Path(path).read_text())
    if packet.get("schema")!="tracehoi.PostQ2Config.v1": raise RuntimeError("post-Q2 config schema")
    if tuple(packet.get("stage_order",()))!=STAGES: raise RuntimeError("post-Q2 stage order")
    return packet
def make_dag(config,run_root):
    return RestartableCaseDAG(config["case_id"],run_root,config["owner_bundle"],config["roots"],stage_order=STAGES)
def plan(config_path):
    config=load_config(config_path)
    return {"schema":"tracehoi.PostQ2Plan.v1","case_id":config["case_id"],
      "accepted_terminal_schemas":["tracehoi.FoundationTerminalPass.v1","tracehoi.Q2TerminalResult.v1"],
      "stage_order":list(STAGES),"execution":{"gate_a":"real","frame_i":"real","gate_c":"real","d0_and_later":"not_yet_real"},
      "decision":"post_Q2_plan_closed"}
def status(config_path,run_root):
    config=load_config(config_path); return make_dag(config,run_root).resume()
def run_mock(config_path,foundation_result,run_root,max_stages=None):
    config=load_config(config_path); _assert_mock_run(config,run_root)
    accepted=validate_foundation_terminal(foundation_result)
    if accepted.get("case_id")!=config["case_id"]:
        raise RuntimeError("foundation terminal case mismatch")
    dag=make_dag(config,run_root)
    source=Path(foundation_result).resolve()
    state=dag.start({"foundation_terminal":{"path":str(source),"sha256":sha(source)}})
    count=0
    while int(state["next_index"])<len(STAGES) and (max_stages is None or count<max_stages):
        stage=STAGES[int(state["next_index"])]
        def producer(stage_root,inputs,stage=stage):
            out=stage_root/(stage+"_mock.json")
            out.write_text(json.dumps({"schema":"tracehoi.PostQ2MockArtifact.v1",
              "stage":stage,"inputs":inputs},sort_keys=True)+"\n")
            return {stage:str(out)}
        dag.run_stage(stage,producer); state=dag.resume(); count+=1
    return state
def run_real_gate_a(config_path,gate_a_config,foundation_result,run_root):
    config=load_config(config_path); accepted=validate_foundation_terminal(foundation_result)
    if accepted.get("case_id")!=config["case_id"]:
        raise RuntimeError("foundation terminal case mismatch")
    dag=make_dag(config,run_root); source=Path(foundation_result).resolve()
    state=dag.start({"foundation_terminal":{"path":str(source),"sha256":sha(source)}})
    if int(state["next_index"])!=0:
        if state["history"] and state["history"][0]["stage"]=="gate_a": return state
        raise RuntimeError("real Gate-A can only own the first downstream stage")
    def producer(stage_root,inputs):
        terminal=gate_a_adapter.run(gate_a_config,source,stage_root/"gate_a_runtime")
        terminal_path=stage_root/"gate_a_runtime"/"gate_a_terminal.json"
        if terminal.get("eligible_for_frame_i") is not True: raise RuntimeError("Gate-A is not eligible for frame I")
        return {"gate_a_terminal":str(terminal_path)}
    dag.run_stage("gate_a",producer)
    return dag.resume()
def run_real_frame_i(config_path,frame_i_gate_c_config,run_root):
    config=load_config(config_path); dag=make_dag(config,run_root); state=dag.resume()
    if int(state["next_index"])!=1:
        if len(state.get("history",()))>1 and state["history"][1]["stage"]=="frame_i": return state
        raise RuntimeError("real Frame-I requires one completed real Gate-A stage")
    if not state.get("history") or state["history"][0]["stage"]!="gate_a":
        raise RuntimeError("real Frame-I lineage does not begin at Gate A")
    def producer(stage_root,inputs):
        terminal=frame_i_gate_c_adapter.run_frame_i(frame_i_gate_c_config,stage_root/"frame_i_runtime")
        terminal_path=stage_root/"frame_i_runtime"/"frame_i_terminal.json"
        if terminal.get("eligible_for_gate_c") is not True: raise RuntimeError("Frame-I is not eligible for Gate C")
        return {"frame_i_terminal":str(terminal_path)}
    dag.run_stage("frame_i",producer)
    return dag.resume()
def run_real_gate_c(config_path,frame_i_gate_c_config,run_root):
    config=load_config(config_path); dag=make_dag(config,run_root); state=dag.resume()
    if int(state["next_index"])!=2:
        if len(state.get("history",()))>2 and state["history"][2]["stage"]=="gate_c": return state
        raise RuntimeError("real Gate-C requires completed Gate-A and Frame-I stages")
    if [row["stage"] for row in state.get("history",())[:2]]!=["gate_a","frame_i"]:
        raise RuntimeError("real Gate-C lineage mismatch")
    inputs=state.get("last_outputs",{})
    if set(inputs)!={"frame_i_terminal"}: raise RuntimeError("real Gate-C requires one Frame-I terminal")
    frame_i_terminal=Path(inputs["frame_i_terminal"]["path"])
    if sha(frame_i_terminal)!=inputs["frame_i_terminal"]["sha256"]: raise RuntimeError("Frame-I terminal hash mismatch")
    def producer(stage_root,inputs):
        terminal=frame_i_gate_c_adapter.run_gate_c(frame_i_gate_c_config,frame_i_terminal,stage_root/"gate_c_runtime")
        terminal_path=stage_root/"gate_c_runtime"/"gate_c_terminal.json"
        if terminal.get("eligible_for_d0") is not True: raise RuntimeError("Gate-C is not eligible for D0")
        return {"gate_c_terminal":str(terminal_path)}
    dag.run_stage("gate_c",producer)
    return dag.resume()
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("mode",choices=("plan","status","mock","resume","gate-a-plan","gate-a-run","gate-a-resume","gate-a-audit","frame-i-run","gate-c-run","j0-review","j0-review-resume"))
    parser.add_argument("--config",required=True); parser.add_argument("--run-root")
    parser.add_argument("--gate-a-config")
    parser.add_argument("--frame-i-gate-c-config")
    parser.add_argument("--foundation-pass"); parser.add_argument("--q2-result")
    parser.add_argument("--j0-evidence"); parser.add_argument("--j0-review-root")
    parser.add_argument("--max-stages",type=int); args=parser.parse_args()
    if args.mode=="plan": result=plan(args.config)
    elif args.mode=="status": result=status(args.config,args.run_root)
    elif args.mode in ("j0-review","j0-review-resume"):
        if not args.run_root or not args.j0_evidence or not args.j0_review_root:
            raise RuntimeError("--run-root, --j0-evidence and --j0-review-root are required")
        result=run_j0_review(args.mode,args.config,args.run_root,args.j0_evidence,args.j0_review_root)
    elif args.mode=="resume":
        if not args.run_root: raise RuntimeError("--run-root is required")
        result=resume_guarded(args.config,args.run_root)
    elif args.mode in ("frame-i-run","gate-c-run"):
        if not args.run_root: raise RuntimeError("--run-root is required")
        if not args.frame_i_gate_c_config: raise RuntimeError("--frame-i-gate-c-config is required")
        if args.mode=="frame-i-run": result=run_real_frame_i(args.config,args.frame_i_gate_c_config,args.run_root)
        else: result=run_real_gate_c(args.config,args.frame_i_gate_c_config,args.run_root)
    else:
        supplied=[value for value in (args.foundation_pass,args.q2_result) if value]
        if len(supplied)!=1:
            raise RuntimeError("supply exactly one of --foundation-pass or --q2-result")
        if args.mode=="mock":
            result=run_mock(args.config,supplied[0],args.run_root,args.max_stages)
        else:
            if not args.gate_a_config: raise RuntimeError("--gate-a-config is required")
            gate_root=Path(args.run_root)/"00_gate_a"/"gate_a_runtime"
            if args.mode=="gate-a-plan": result=gate_a_adapter.plan(args.gate_a_config,supplied[0],gate_root)
            elif args.mode=="gate-a-audit": result=gate_a_adapter.audit(args.gate_a_config,supplied[0],gate_root)
            else: result=run_real_gate_a(args.config,args.gate_a_config,supplied[0],args.run_root)
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__": main()
