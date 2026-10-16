"""Seal, preflight, one CPU load service, retain diagnostics even on failure."""
import io,json,os,stat,sys,time,zipfile
from pathlib import Path
from read_helpers import E,H,need,run_helper,file_bytes
from probe_storage import write_file,interpreter_admission,pinned_hash
from native_service import run as native_run
from embedded_prior import verify as verify_prior
_ALLOWED=None
ENV={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'}
def audit(event,args):
 if event in {'os.system','os.posix_spawn','os.fork','socket.connect','ctypes.dlopen'}:raise RuntimeError('parent_forbidden:'+event)
 if event=='subprocess.Popen':need(_ALLOWED is not None and args[0]=='/usr/bin/busctl'and args[1]==_ALLOWED and args[2]is None and args[3]==ENV,'parent_exact_helper')
 if event=='import'and args and str(args[0]).split('.')[0]in {'torch','numpy','PIL','safetensors','trimesh','hy3dgen'}:raise RuntimeError('native_imports_only_in_worker')
def guarded(argv,check):
 global _ALLOWED
 need(_ALLOWED is None,'helper_reentry');_ALLOWED=list(argv)
 try:return run_helper(argv,check)
 finally:_ALLOWED=None

def startup():
 r=dict(platform=sys.platform,version=list(sys.version_info),uid=os.geteuid(),isolated=sys.flags.isolated,no_site=sys.flags.no_site,dont_write_bytecode=sys.dont_write_bytecode)
 need(r==dict(platform='linux',version=[3,10,20,'final',0],uid=1000,isolated=1,no_site=1,dont_write_bytecode=True),'server_startup');return r

def run(plan,components,startup_check=startup,service=native_run,interpreter_check=interpreter_admission,install_audit=True):
 need(set(components)==set(plan['components'])and all(H(v)==plan['components'][k]for k,v in components.items()),'sealed_components')
 root=Path(plan['root']);need(not root.exists()and not root.is_symlink(),'fresh_output_root')
 for p in reversed(root.parents):need(stat.S_ISDIR(p.lstat().st_mode),'real_parent_directory')
 root.mkdir(mode=0o700);started=time.monotonic()
 def check():need(time.monotonic()-started<480,'parent_deadline')
 r=dict(schema='HunyuanCPULoadProbeReport.v1',attempt_id=plan['attempt_id'],review_complete=False,errors=[],prior=[],source_preflight=[],support_preflight=[],interpreter={},service={},model_executed=False,weights_loaded=False,cuda_api_invoked_by_probe=False,full_parent_acceptance=False,p2_satisfied=False)
 try:
  r['startup']=startup_check()
  if install_audit:sys.addaudithook(audit)
  r['prior']=verify_prior(plan['prior_evidence'],components)
  interpreter_check(plan['interpreter'],check,r['interpreter'])
  for row in plan['worker_plan']['modules']:
   obs={};r['source_preflight'].append(obs);raw=file_bytes(row['path'],2*1048576,check,obs);need(H(raw)==row['binding'],'native_source_pin:'+row['module'])
  for row in plan['worker_plan'].get('support_sources',[]):
   obs={};r['support_preflight'].append(obs);raw=file_bytes(row['path'],2*1048576,check,obs);need(H(raw)==row['binding'],'support_source_pin:'+row['id'])
  for name in ['native_worker.py','worker_plan.json']:write_file(root,name,components[name])
  for name in ['cache','cache/warp','tmp','config','config/matplotlib']:(root/name).mkdir(mode=0o700)
  service(plan,check,r['service'],helper=guarded)
  need(r['service'].get('complete')is True and not r['service'].get('errors'),'cpu_load_probe_incomplete');r['review_complete']=True
 except BaseException as e:r['errors'].append(dict(type=type(e).__name__,message=str(e)[:500]))
 r['weights_loaded']=r['service'].get('native_result',{}).get('weights_loaded',False)if r['service'].get('native_result')else False
 r['elapsed_seconds']=time.monotonic()-started
 # Include files already staged exactly; never overwrite or remove partial output.
 saved={**components,'review_plan.json':E(plan),'review_report.json':E(r)}
 for name in ['native_ready.json','native_go.json','native_result.json']+['cpu_progress_%02d.json'%i for i in range(32)]:
  p=root/name
  if p.exists():
   obs={};saved[name]=file_bytes(str(p),1048576,lambda:None,obs,owner=os.geteuid())
 for n,b in saved.items():
  p=root/n
  if p.exists():need(p.read_bytes()==b,'existing_output_changed:'+n)
  else:write_file(root,n,b)
 manifest=E(dict(schema='CompactReviewManifest.v1',members=[dict(name=n,**H(b))for n,b in sorted(saved.items())]));saved['transfer_manifest.json']=manifest;write_file(root,'transfer_manifest.json',manifest)
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED)as z:
  for n,b in sorted(saved.items()):z.writestr(n,b)
 raw=buf.getvalue();need(len(raw)<=8*1048576,'zip_cap');receipt=write_file(root,plan['zip_name'],raw)
 fd=os.open(str(root),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:os.fsync(fd)
 finally:os.close(fd)
 s=r['service'];qs=s.get('transport',{}).get('queries',[])
 out=dict(zip=str(root/plan['zip_name']),binding=H(raw),zip_readback=receipt,directory_fsync_close_returned=True,members=len(saved),review_complete=r['review_complete'],errors=r['errors'],service_errors=s.get('errors',[]),host_available_bytes=s.get('memory_admission',{}).get('host_available_bytes'),native_imports_passed=s.get('native_imports_passed',False),cleanup_verified=s.get('cleanup_verified',False),service_submitted=s.get('service_submitted',False),stop_attempted=s.get('stop_attempted',False),manager_calls_attempted=sum(bool(q.get('attempted'))for q in qs),model_executed=False,weights_loaded=r['weights_loaded'],cpu_load_passed=s.get('cpu_load_passed',False),models_constructed=(s.get('native_result')or{}).get('cpu_load',{}).get('models_constructed',[]),cuda_api_invoked_by_probe=False,full_parent_acceptance=False)
 print('HUNYUAN_CPU_BUDGET_PROBE_RETURNED='+json.dumps(out,sort_keys=True));return 0 if r['review_complete']else 1
