from pathlib import Path
import base64,copy,hashlib,io,json,subprocess,sys,tempfile,zipfile
from read_helpers import E,H
N=Path(__file__).resolve().parent;checks=[]
def ck(v,n):
 if not v:raise AssertionError(n)
 checks.append(n)
source=(N/'hunyuan_cpu_budget_probe_P8m5Dv2M_server.sh').read_text();loader=source.split("<<'P8_CPU_LOAD'\n",1)[1].split('\nP8_CPU_LOAD\n',1)[0];loader=loader[:loader.index('raise SystemExit(sys.modules')]
# Exact sealed module loading followed by inert callbacks. All output is local.
for mode in ['complete','native_failure','prior_missing','source_mismatch','support_mismatch','occupied_root','tampered_component']:
 with tempfile.TemporaryDirectory()as temp:
  root=Path(temp).resolve();target=root/'run';prior=root/'prior.txt';prior.write_bytes(b'prior evidence');src=root/'module.py';src.write_bytes(b'x=1\n')
  inject='''
from pathlib import Path
import copy
p=copy.deepcopy(bundle['plan']);p['root']=TARGET
assert 'prior_inputs' not in p
assert all(not Path('/definitely-absent-prior-server-path/'+x['terminal']['name']).exists() for x in p['prior_evidence'])
p['worker_plan']['modules']=[dict(module='inert',path=SOURCE,binding=SOURCE_HASH)]
p['worker_plan']['support_sources']=[]
def service(p,check,r,helper):
 r.update(complete=MODE!='native_failure',errors=[]if MODE!='native_failure'else[{'message':'inert import error'}],cleanup_verified=True,native_imports_passed=MODE!='native_failure',transport={'queries':[]})
def interpreter(p,check,r):r.update(complete=True,errors=[])
if MODE=='tampered_component':components['native_worker.py']+=b'changed'
if MODE=='prior_missing':p['prior_evidence'][0]['terminal']['name']='missing-original-terminal.txt'
if MODE=='source_mismatch':p['worker_plan']['modules'][0]['binding']['sha256']='0'*64
if MODE=='support_mismatch':p['worker_plan']['support_sources']=[dict(id='fixture',path=SOURCE,binding=dict(bytes=SOURCE_HASH['bytes'],sha256='0'*64))]
try:code=sys.modules['review_driver'].run(p,components,startup_check=lambda:{'local_fixture':True},service=service,interpreter_check=interpreter,install_audit=False)
except ValueError as e:print('EXPECTED_REFUSAL='+str(e));code=3
raise SystemExit(code)
'''
  vals=dict(TARGET=str(target),PRIOR=str(prior),HASH=H(prior.read_bytes())['sha256'],SOURCE=str(src),SOURCE_HASH=H(src.read_bytes()),MODE=mode)
  text=loader+'\n'+''.join(k+'='+repr(v)+'\n'for k,v in vals.items())+inject
  if mode=='occupied_root':target.mkdir();(target/'keep').write_bytes(b'original')
  result=subprocess.run([sys.executable,'-I','-S','-B','-'],input=text.encode(),capture_output=True,timeout=15)
  ck(result.returncode==(0 if mode=='complete'else 3 if mode in ['occupied_root','tampered_component']else 1),'sealed_status:'+mode+':'+result.stderr.decode()[-300:])
  if mode in ['occupied_root','tampered_component']:
   ck(not list(target.glob('*.zip'))if target.exists()else True,'no_packet_on_scope_refusal:'+mode)
   if mode=='occupied_root':ck((target/'keep').read_bytes()==b'original','occupied_preserved')
  else:
   packet=target/json.loads((N/'review_plan.json').read_bytes())['zip_name']
   with zipfile.ZipFile(packet)as z:
    ck(z.testzip()is None and packet.stat().st_size<=8*1048576 and sum(n.endswith('.zip')for n in z.namelist())==1 and len(z.namelist())==25,'sealed_archive:'+mode);r=json.loads(z.read('review_report.json'));ck(r['review_complete']==(mode=='complete')and r['attempt_id']=='P8m5Dv2M','sealed_report:'+mode)
    if mode!='prior_missing':ck(len(r['prior'])==1 and all(x['original_archive_rechecked']is True and x['prior_server_paths_read']is False for x in r['prior']),'embedded_prior_verified:'+mode)
    if mode in ['complete','native_failure']:ck(all((target/x).is_dir()and (target/x).stat().st_mode&0o777==0o700 for x in ['config','config/matplotlib','cache/warp']),'private_configuration_staged:'+mode)
    if mode in ['prior_missing','source_mismatch','support_mismatch']:ck(r['service']=={},'no_service_after_preflight_failure:'+mode)
# Native worker entry point in a local child, with only the stdlib json module.
for mode in ['success','import_failure']:
 with tempfile.TemporaryDirectory()as temp:
  root=Path(temp).resolve();worker=root/'native_worker.py';worker.write_bytes((N/'native_worker.py').read_bytes());module=Path(json.__file__).resolve()
  p=dict(attempt_id='P8m5Dv2M',root=str(root),worker_binding=H(worker.read_bytes()),modules=[dict(module='json'if mode=='success'else'no_such_hunyuan_probe_module',path=str(module),binding=H(module.read_bytes()))],environment={},import_paths=[])
  raw=E(p);(root/'worker_plan.json').write_bytes(raw);binding=H(raw)
  code="import os,sys;os.geteuid=lambda:1000;sys.argv=["+repr(str(worker))+","+repr(binding['sha256'])+"];ns={'__name__':'fixture','__file__':sys.argv[0]};exec(compile(open(sys.argv[0],'rb').read(),sys.argv[0],'exec'),ns);ns['perform_cpu_load']=lambda p,r,d:r.update(cpu_load={'weights_loaded':True});raise SystemExit(ns['main']())"
  proc=subprocess.Popen([sys.executable,'-I','-S','-B','-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  (root/'native_go.json').write_bytes(E(dict(pid=proc.pid,plan_binding=binding)))
  stdout,stderr=proc.communicate(timeout=10)
  ck(proc.returncode==0,'child_diagnostic_exit:'+mode+':'+stderr.decode()[-300:]);r=json.loads((root/'native_result.json').read_bytes())
  ck(r['complete']==(mode=='success')and bool(r['errors'])==(mode!='success'),'child_result:'+mode);ck(r['pid']==proc.pid and r['model_executed']is False,'child_identity_scope:'+mode)
(N/('sealed_tests_python'+str(sys.version_info.major)+str(sys.version_info.minor)+'.json')).write_bytes(E(dict(passed=True,count=len(checks),checks=checks,server_contacted=False,native_dependencies_imported=False)));print('SEALED',len(checks))
