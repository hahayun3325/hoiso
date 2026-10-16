"""Verify K4's captured helper evidence and J3/H2 chain as data only."""
import io,json,stat,zipfile
from pathlib import Path
from read_helpers import H,need

def verify_g9(plan,components):
    p=plan['prior'];raw=components[p['packet_name']];terminal=components[p['terminal_name']]
    need(H(raw)==p['packet_binding'] and H(terminal)==p['terminal_binding'],'prior_binding')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        entries=z.infolist();names=z.namelist()
        need(len(names)==len(set(names))==33 and all(Path(x.filename).name==x.filename
             and not x.is_dir() and not stat.S_ISLNK(x.external_attr>>16)
             and x.file_size<=8*1048576 for x in entries)
             and sum(x.file_size for x in entries)<=16*1048576,'prior_zip_scope')
        need(z.testzip() is None,'prior_crc')
        report=json.loads(z.read('review_report.json'));native=json.loads(z.read('native_result.json'))
        need(H(z.read('review_report.json'))==p['report_binding'],'prior_report_binding')
    s=report['service']
    need(report['attempt_id']=='G9e6Wn3E' and not report['review_complete']
         and report['errors']==[dict(type='ValueError',message='native_import_probe_incomplete')]
         and s['native_result']==native and s['cleanup_verified'] is True
         and s['service_submitted'] is True and s['stop_request_accepted'] is True
         and s['native_imports_passed'] is False,'prior_outcome')
    need(len(native['modules'])==7 and all(x['returned'] for x in native['modules'][:6])
         and native['modules'][5]['module']=='pytorch3d'
         and native['modules'][6]==dict(module='hy3dgen.shapegen.models.hunyuan3ddit',returned=False),'prior_imports')
    err=native['errors']
    need(len(err)==1 and err[0]['type']=='RuntimeError'
         and err[0]['message']=='import_probe_forbidden:subprocess.Popen'
         and 'cpu_name = platform.processor()' in err[0]['traceback']
         and 'wp.init()' in err[0]['traceback'],'prior_failure')
    need(native['audit_denials'][-1]==dict(event='subprocess.Popen',argv=['uname','-p'],
              path='uname',reason='import_probe_forbidden:subprocess.Popen'),'prior_uname_denial')
    lines=terminal.decode().splitlines();tag='HUNYUAN_NATIVE_PATH_RECOVERY_PROBE_RETURNED='
    rows=[json.loads(x[len(tag):]) for x in lines if x.startswith(tag)]
    need(len(rows)==1 and rows[0]['binding']==H(raw) and rows[0]['members']==33
         and rows[0]['cleanup_verified'] is True and rows[0]['review_complete'] is False
         and lines[-2:]==['RUN_EXIT_STATUS=1','TERMINAL_CAPTURE_EXIT_STATUS=0'], 'prior_terminal')
    return dict(attempt_id='G9e6Wn3E',packet_binding=H(raw),terminal_binding=H(terminal),
                original_archive_rechecked=True,cleanup_verified=True,native_imports_passed=False,
                failing_module=native['modules'][-1]['module'],blocked_argv=['uname','-p'],
                prior_server_paths_read=False)

def verify_h2(spec,components):
    need(type(spec)is list and len(spec)==1 and spec[0]['attempt_id']=='H2f9Xp6F','prerequisite_attempt')
    item=spec[0];raw=components[item['packet']['name']];terminal=components[item['terminal']['name']]
    need(H(raw)==item['packet']['binding']and H(terminal)==item['terminal']['binding'],'embedded_original_binding')
    with zipfile.ZipFile(io.BytesIO(raw))as z:
        entries=z.infolist();names=z.namelist()
        need(len(names)==len(set(names))==21 and all(Path(x.filename).name==x.filename
             and not x.is_dir()and not stat.S_ISLNK(x.external_attr>>16)and x.file_size<=2*1048576 for x in entries)
             and sum(x.file_size for x in entries)<=8*1048576,'h2_archive_scope')
        need(z.testzip()is None,'h2_crc');saved={name:z.read(name)for name in names}
    need(H(saved['review_report.json'])==item['report_binding'],'h2_report_binding')
    report=json.loads(saved['review_report.json']);priorplan=json.loads(saved['review_plan.json'])
    need(report['attempt_id']=='H2f9Xp6F'and report['review_complete']is True and report['errors']==[]
         and report['source_files_captured']==12 and report['source_bytes_captured']==813043,'h2_source_capture')
    need(report['prior']==verify_g9(priorplan,saved),'h2_g9_join')
    captured={row['id']:row for row in report['sources']if row['status']=='captured'}
    need(set(captured)=={row['id']for row in item['captured_sources']},'h2_source_set')
    for row in item['captured_sources']:
        got=captured[row['id']]
        need(got['path']==row['path']and got['binding']==row['binding']==H(saved[got['member']]),'h2_source_binding')
        before=got['observation'];after=got['recheck']
        need(before['complete']and after['complete']and before['errors']==after['errors']==[]
             and before['binding']==after['binding']==row['binding']and before['after']==after['before']
             and before['route']==after['route'],'h2_source_stability')
    need(all(report[k]is False for k in ['manager_contacted','service_submitted','model_executed',
         'weights_loaded','native_imports_executed','cuda_api_invoked_by_review','permissions_changed']), 'h2_scope')
    lines=terminal.decode().splitlines();tag='HUNYUAN_NATIVE_WARP_REVIEW_RETURNED='
    rows=[json.loads(line[len(tag):])for line in lines if line.startswith(tag)]
    need(len(rows)==1 and rows[0]['binding']==H(raw)and rows[0]['members']==21
         and rows[0]['review_complete']is True and rows[0]['errors']==[]
         and lines[-2:]==['RUN_EXIT_STATUS=0','TERMINAL_CAPTURE_EXIT_STATUS=0']
         and 'HUNYUAN_NATIVE_WARP_REVIEW_COMMAND_EXIT_STATUS=0'in lines,'h2_terminal_join')
    return [dict(attempt_id='H2f9Xp6F',mode='embedded_verified_originals',status='VERIFIED_SUCCESS',
                 packet=item['packet'],terminal=item['terminal'],report_binding=item['report_binding'],
                 complete=True,original_archive_rechecked=True,server_original_paths_checked=False,
                 nested_G9=report['prior'])]


def verify_j3(plan,components):
    p=plan['prior'];raw=components[p['packet_name']];terminal=components[p['terminal_name']]
    need(H(raw)==p['packet_binding'] and H(terminal)==p['terminal_binding'],'prior_binding')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        entries=z.infolist();names=z.namelist()
        need(len(names)==len(set(names))==23 and all(Path(x.filename).name==x.filename
             and not x.is_dir() and not stat.S_ISLNK(x.external_attr>>16)
             and x.file_size<=8*1048576 for x in entries)
             and sum(x.file_size for x in entries)<=16*1048576,'prior_zip_scope')
        need(z.testzip() is None,'prior_crc')
        report=json.loads(z.read('review_report.json'));native=json.loads(z.read('native_result.json'))
        need(H(z.read('review_report.json'))==p['report_binding'],'prior_report_binding')
    s=report['service']
    need(report['attempt_id']=='J3g8Yq5G' and not report['review_complete']
         and report['errors']==[dict(type='ValueError',message='native_import_probe_incomplete')]
         and s['native_result']==native and s['cleanup_verified'] is True
         and s['service_submitted'] is True and s['stop_request_accepted'] is True
         and s['native_imports_passed'] is False,'prior_outcome')
    need(len(native['modules'])==7 and all(x['returned'] for x in native['modules'][:6])
         and native['modules'][5]['module']=='pytorch3d'
         and native['modules'][6]==dict(module='hy3dgen.shapegen.models.hunyuan3ddit',returned=False),'prior_imports')
    err=native['errors']
    need(len(err)==1 and err[0]['type']=='ModuleNotFoundError'
         and err[0]['message']=="No module named 'utilz'"
         and 'import utilz.kaolin_sdf_ops as kaolin_sdf' in err[0]['traceback'],'prior_failure')
    need(native['audit_denials'][-1]==dict(event='subprocess.Popen',argv=['uname','-p'],
              path='uname',reason="[Errno 13] import_probe_forbidden:subprocess.Popen: 'uname'",
              action='blocked_optional_processor_discovery',errno=13,error_type='PermissionError'),'prior_uname_fallback')
    lines=terminal.decode().splitlines();tag='HUNYUAN_NATIVE_PROCESSOR_FALLBACK_PROBE_RETURNED='
    rows=[json.loads(x[len(tag):]) for x in lines if x.startswith(tag)]
    need(len(rows)==1 and rows[0]['binding']==H(raw) and rows[0]['members']==23
         and rows[0]['cleanup_verified'] is True and rows[0]['review_complete'] is False
         and lines[-2:]==['RUN_EXIT_STATUS=1','TERMINAL_CAPTURE_EXIT_STATUS=0'], 'prior_terminal')
    return dict(attempt_id='J3g8Yq5G',packet_binding=H(raw),terminal_binding=H(terminal),
                original_archive_rechecked=True,cleanup_verified=True,native_imports_passed=False,
                failing_module=native['modules'][-1]['module'],missing_module='utilz',
                prior_server_paths_read=False)

def verify_k4(spec,components):
    need(type(spec)is list and len(spec)==1 and spec[0]['attempt_id']=='K4h9Zr6H','prerequisite_attempt')
    item=spec[0];raw=components[item['packet']['name']];terminal=components[item['terminal']['name']]
    need(H(raw)==item['packet']['binding']and H(terminal)==item['terminal']['binding'],'embedded_original_binding')
    with zipfile.ZipFile(io.BytesIO(raw))as z:
        entries=z.infolist();names=z.namelist()
        need(len(names)==len(set(names))==19 and all(Path(x.filename).name==x.filename
             and not x.is_dir()and not stat.S_ISLNK(x.external_attr>>16)and x.file_size<=2*1048576 for x in entries)
             and sum(x.file_size for x in entries)<=8*1048576,'k4_archive_scope')
        need(z.testzip()is None,'k4_crc');saved={name:z.read(name)for name in names}
    need(H(saved['review_report.json'])==item['report_binding'],'k4_report_binding')
    report=json.loads(saved['review_report.json']);priorplan=json.loads(saved['review_plan.json'])
    need(report['attempt_id']=='K4h9Zr6H'and report['review_complete']is False
         and report['errors']==[dict(stage='census',type='ValueError',message='census_incomplete')]
         and report['source_files_captured']==9 and report['source_bytes_captured']==197799
         and report['dependency_files_found']is True and report['dependency_available']is False,'k4_capture_outcome')
    census=report['census']
    need(census['errors']==[dict(type='ValueError',message='census_depth_limit')]
         and census['candidates']==['/home/fredcui/Projects/FollowMyHold/third_party/utilz/'+n
                                   for n in ['__init__.py','code_utils.py','kaolin_sdf_ops.py']],'k4_helper_locations')
    need(report['prior']==verify_j3(priorplan,saved),'k4_j3_join')
    with zipfile.ZipFile(io.BytesIO(saved[priorplan['prior']['packet_name']]))as z:
        j3={n:z.read(n)for n in z.namelist()}
    j3plan=json.loads(j3['review_plan.json']);j3report=json.loads(j3['review_report.json'])
    need(j3report['prior']==verify_h2(j3plan['prior_evidence'],j3),'j3_h2_join')
    captured={row['id']:row for row in report['sources']if row['status']=='captured'}
    need(set(captured)=={row['id']for row in item['captured_sources']},'k4_source_set')
    for row in item['captured_sources']:
        got=captured[row['id']]
        need(got['path']==row['path']and got['binding']==row['binding']==H(saved[got['member']]),'k4_source_binding')
        before=got['observation'];after=got['recheck']
        need(before['complete']and after['complete']and before['errors']==after['errors']==[]
             and before['binding']==after['binding']==row['binding']and before['after']==after['before']
             and before['route']==after['route'],'k4_source_stability')
    need(all(report[k]is False for k in ['manager_contacted','service_submitted','model_executed',
         'weights_loaded','native_imports_executed','cuda_api_invoked_by_review','permissions_changed']), 'k4_scope')
    lines=terminal.decode().splitlines();tag='HUNYUAN_NATIVE_UTILZ_REVIEW_RETURNED='
    rows=[json.loads(line[len(tag):])for line in lines if line.startswith(tag)]
    need(len(rows)==1 and rows[0]['binding']==H(raw)and rows[0]['members']==19
         and rows[0]['review_complete']is False and rows[0]['errors']==report['errors']
         and lines[-2:]==['RUN_EXIT_STATUS=1','TERMINAL_CAPTURE_EXIT_STATUS=0']
         and 'HUNYUAN_NATIVE_UTILZ_REVIEW_COMMAND_EXIT_STATUS=1'in lines,'k4_terminal_join')
    return [dict(attempt_id='K4h9Zr6H',mode='embedded_verified_originals',status='VERIFIED_HOLD',
                 packet=item['packet'],terminal=item['terminal'],report_binding=item['report_binding'],
                 captured_helpers_verified=True,census_complete=False,original_archive_rechecked=True,
                 server_original_paths_checked=False,nested_J3=report['prior'])]

def unpack_original(item,components,count):
    raw=components[item['packet']['name']];terminal=components[item['terminal']['name']]
    need(H(raw)==item['packet']['binding']and H(terminal)==item['terminal']['binding'],'embedded_original_binding')
    with zipfile.ZipFile(io.BytesIO(raw))as z:
        entries=z.infolist();names=z.namelist()
        need(len(names)==len(set(names))==count and all(Path(x.filename).name==x.filename
             and not x.is_dir()and not stat.S_ISLNK(x.external_attr>>16)and x.file_size<=2*1048576 for x in entries)
             and sum(x.file_size for x in entries)<=8*1048576,'original_archive_scope')
        need(z.testzip()is None,'original_crc');saved={name:z.read(name)for name in names}
    need(H(saved['review_report.json'])==item['report_binding'],'original_report_binding')
    manifest=json.loads(saved['transfer_manifest.json'])['members']
    need(len(manifest)==len(names)-1 and {x['name']for x in manifest}==set(names)-{'transfer_manifest.json'},'original_manifest_scope')
    for x in manifest:need(H(saved[x['name']])=={k:x[k]for k in ['bytes','sha256']},'original_manifest_binding')
    return saved,json.loads(saved['review_report.json']),terminal.decode().splitlines()

def verify(spec,components):
    need(type(spec)is list and [x['attempt_id']for x in spec]==['L5j2As7J','P8m5Dv2H'],'prerequisite_attempts')
    item=spec[0];saved,r,lines=unpack_original(item,components,23);p=json.loads(saved['review_plan.json'])
    need(r['attempt_id']=='L5j2As7J'and r['review_complete']is False
         and r['errors']==[dict(type='ValueError',message='native_import_probe_incomplete')],'l5_outcome')
    need(r['prior']==verify_k4(p['prior_evidence'],saved),'l5_k4_join')
    s=r['service'];n=json.loads(saved['native_result.json'])
    need(s['native_result']==n and s['cleanup_verified']is True and s['stop_request_accepted']is True
         and s['service_submitted']is True and s['native_imports_passed']is False,'l5_cleanup')
    need(len(n['modules'])==10 and n['modules'][:9]==[dict(module=x['module'],name=x['module'],path=x['path'],returned=True)for x in p['worker_plan']['modules'][:9]]
         and n['modules'][9]==dict(module='hy3dgen.shapegen.models.hunyuan3ddit',returned=False),'l5_imports')
    need(len(n['errors'])==1 and n['errors'][0]['type']=='ModuleNotFoundError'
         and n['errors'][0]['message']=="Could not import module 'CLIPVisionModelWithProjection'. Are this object's requirements defined correctly?",'l5_wrapped_error')
    trace=n['errors'][0]['traceback']
    need(all(x in trace for x in ['from hqq.core.quantize import Quantizer as HQQQuantizer','AsyncCompile.warm_pool()',
         'pool = SubprocPool(config.compile_threads)','RuntimeError: import_probe_forbidden:subprocess.Popen']),'l5_compiler_chain')
    denial=n['audit_denials'][-1]
    need(denial==dict(event='subprocess.Popen',path=p['interpreter']['path'],reason='import_probe_forbidden:subprocess.Popen',argv=[p['interpreter']['path'],'/home/fredcui/anaconda3/envs/foho/lib/python3.10/site-packages/torch/_inductor/compile_worker/__main__.py','--workers=12','--parent=368746','--read-fd=9','--write-fd=12']),'l5_compiler_denial')
    tag='HUNYUAN_NATIVE_UTILZ_PATH_PROBE_RETURNED=';summaries=[json.loads(x[len(tag):])for x in lines if x.startswith(tag)]
    need(len(summaries)==1 and summaries[0]['binding']==item['packet']['binding']and summaries[0]['members']==23
         and summaries[0]['errors']==r['errors']and summaries[0]['cleanup_verified']is True
         and lines[-2:]==['RUN_EXIT_STATUS=1','TERMINAL_CAPTURE_EXIT_STATUS=0'],'l5_terminal')
    out=[dict(attempt_id='L5j2As7J',mode='embedded_verified_originals',status='VERIFIED_HOLD',packet=item['packet'],
              terminal=item['terminal'],report_binding=item['report_binding'],original_archive_rechecked=True,
              server_original_paths_checked=False,cleanup_verified=True,utilz_imports_returned=True,
              compiler_helper_launch_blocked=True,native_imports_passed=False)]
    item=spec[1];saved,r,lines=unpack_original(item,components,14);p=json.loads(saved['review_plan.json'])
    need(r['attempt_id']=='P8m5Dv2H'and r['review_complete']is True and r['errors']==[]
         and r['model_executed']is False and r['runtime_authorized']is False,'p8_source_only')
    need({x['id']for x in item['captured_sources']}=={'async_compile','inductor_config'},'compiler_source_set')
    for row in item['captured_sources']:
        need(H(saved[row['member']])==row['binding'],'compiler_source_binding')
        source=next(x for x in p['inputs']if x['role']==row['id'])
        need(source['path']==row['path']and source['binding']==row['binding'],'compiler_source_path_pin')
        reads=[x for x in r['reads']if x['path']==row['path']and x['phase']in ['before','after']]
        need(len(reads)==2 and {x['phase']for x in reads}=={'before','after'},'compiler_paired_reads')
        for x in reads:
            need(x['binding']==row['binding']and x['before']==x['after']
                 and x['opened_identity']==x['end_identity']==x['before']['identity']
                 and x['close_returned']is True and x['error']is None,'compiler_source_stability')
        need(reads[0]['after']==reads[1]['before'],'compiler_pair_stability')
    tag='MODEL_WORKER_INDUCTOR_SOURCE_REVIEW_RETURNED=';summaries=[json.loads(x[len(tag):])for x in lines if x.startswith(tag)]
    need(len(summaries)==1 and summaries[0]['binding']==item['packet']['binding']and summaries[0]['members']==14
         and summaries[0]['review_complete']is True and summaries[0]['errors']==[]
         and lines[-2:]==['RUN_EXIT_STATUS=0','TERMINAL_CAPTURE_EXIT_STATUS=0'],'p8_terminal')
    out.append(dict(attempt_id='P8m5Dv2H',mode='embedded_verified_originals',status='VERIFIED_SUCCESS',packet=item['packet'],
               terminal=item['terminal'],report_binding=item['report_binding'],original_archive_rechecked=True,
               server_original_paths_checked=False,captured_compiler_controls_verified=True))
    return out

verify_m6_ancestors=verify

def verify(spec,components):
 need(type(spec)is list and len(spec)==1 and spec[0]['attempt_id']=='M6k3Bt8K','m6_prerequisite')
 saved,r,lines=unpack_original(spec[0],components,25);p=json.loads(saved['review_plan.json']);s=r['service'];n=json.loads(saved['native_result.json']);wp=p['worker_plan']
 need(r['review_complete']is True and r['errors']==[]and r['attempt_id']=='M6k3Bt8K','m6_success')
 need(r['prior']==verify_m6_ancestors(p['prior_evidence'],saved),'m6_prior_join')
 need(s['native_result']==n and s['complete']is True and s['cleanup_verified']is True and s['native_imports_passed']is True and s['stop_request_accepted']is True and s['exit']==dict(ExecMainCode=1,ExecMainStatus=0,Result='success'),'m6_lifecycle')
 need(n['complete']is True and n['errors']==[]and n['plan_binding']==p['worker_plan_binding']and n['pid']==s['identity']['pid'],'m6_result')
 need(n['modules']==[dict(module=x['module'],name=x['module'],path=x['path'],returned=True)for x in wp['modules']],'m6_imports')
 for prefix,rows in [('',wp['modules']),('support_',wp['support_sources'])]:
  before=n[prefix+'sources_before'];need(before==n[prefix+'sources_after']==n[prefix+'preflight']and len(before)==len(rows),'m6_source_rechecks')
  for want,got in zip(rows,before):need(want['binding']==got['binding']and want['path']==got['path'],'m6_sources')
 need(wp['environment']['TORCHINDUCTOR_COMPILE_THREADS']=='1'and all(n[k]is False for k in ['weights_loaded','model_executed','cuda_api_invoked_by_probe']),'m6_scope')
 tag='HUNYUAN_NATIVE_COMPILER_SERIAL_PROBE_RETURNED=';summaries=[json.loads(x[len(tag):])for x in lines if x.startswith(tag)]
 need(len(summaries)==1 and summaries[0]['binding']==spec[0]['packet']['binding']and summaries[0]['review_complete']is True and summaries[0]['native_imports_passed']is True and summaries[0]['cleanup_verified']is True and lines[-2:]==['RUN_EXIT_STATUS=0','TERMINAL_CAPTURE_EXIT_STATUS=0'],'m6_terminal')
 return [dict(attempt_id='M6k3Bt8K',original_archive_rechecked=True,packet_binding=spec[0]['packet']['binding'],terminal_binding=spec[0]['terminal']['binding'],native_imports_passed=True,cleanup_verified=True,prior_server_paths_read=False)]

verify_m6=verify

def verify(spec,components):
 need(type(spec)is list and len(spec)==1 and spec[0]['attempt_id']=='N7l4Cu9L','n7_prerequisite')
 saved,r,lines=unpack_original(spec[0],components,24);p=json.loads(saved['review_plan.json']);s=r['service']
 need(r['attempt_id']=='N7l4Cu9L'and r['review_complete']is False and r['errors']==[dict(type='ValueError',message='cpu_load_probe_incomplete')],'n7_hold')
 need(r['prior']==verify_m6(p['prior_evidence'],saved),'n7_m6_join')
 need(s['errors']==[dict(type='ValueError',message='host_memory_headroom_28GiB')],'n7_memory_refusal')
 need(all(s[k]is False for k in ['service_submitted','submission_attempted','stop_attempted','stop_request_accepted','complete','cpu_load_passed','model_executed'])and s['native_result']is None and s['writes']==[]and s['properties']==[],'n7_no_worker')
 need(s['memory_admission']['host_available_bytes']==28820393984 and s['memory_admission']['host']['complete']is True and not s['memory_admission']['host']['errors'],'n7_recorded_memory')
 qs=s['transport']['queries'];need(len(qs)==17 and all(q['kind']=='read'and q['complete']for q in qs)and s['transport']['complete']and not s['transport']['errors'],'n7_read_only_manager')
 tag='HUNYUAN_CPU_LOAD_PROBE_RETURNED=';summaries=[json.loads(x[len(tag):])for x in lines if x.startswith(tag)]
 need(len(summaries)==1 and summaries[0]['binding']==spec[0]['packet']['binding']and summaries[0]['service_submitted']is False and summaries[0]['review_complete']is False and summaries[0]['models_constructed']==[]and lines[-2:]==['RUN_EXIT_STATUS=1','TERMINAL_CAPTURE_EXIT_STATUS=0'],'n7_terminal')
 return [dict(attempt_id='N7l4Cu9L',original_archive_rechecked=True,packet_binding=spec[0]['packet']['binding'],terminal_binding=spec[0]['terminal']['binding'],service_submitted=False,recorded_host_available_bytes=28820393984,prior_server_paths_read=False)]
