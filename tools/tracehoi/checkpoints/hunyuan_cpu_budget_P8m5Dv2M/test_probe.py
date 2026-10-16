from pathlib import Path
import copy,json,os,sys,tempfile,types
from unittest.mock import patch
import native_service as ns,native_worker as nw
from read_helpers import E,H
N=Path(__file__).resolve().parent;P=N.parent/'hunyuan_completion_end_to_end_return_20261014/packet';actual=json.loads((P/'review_report.json').read_bytes())['delivery'];plan=json.loads((N/'review_plan.json').read_bytes());checks=[]
def ck(v,n):
 if not v:raise AssertionError(n)
 checks.append(n)
def raises(fn,n):
 try:fn()
 except (ValueError,RuntimeError,ImportError):ck(True,n)
 else:raise AssertionError(n)
# Actual file identity checks and import callbacks; no native dependencies loaded.
for mode in ['success','wrong_origin','changed_source','raises','symlink']:
 with tempfile.TemporaryDirectory()as temp:
  root=Path(temp).resolve();p=root/'module.py';p.write_bytes(b'x=1\n');row=dict(module='testmodule',path=str(p),binding=H(p.read_bytes()))
  if mode=='symlink':q=root/'actual.py';q.write_bytes(p.read_bytes());p.unlink();p.symlink_to(q)
  def importer(name):
   if mode=='raises':raise ImportError('synthetic missing library')
   if mode=='changed_source':p.write_bytes(b'x=2\n')
   return types.SimpleNamespace(__name__=name,__file__=str(p)if mode!='wrong_origin'else'/wrong/module.py')
  r={}
  if mode=='success':nw.imports(dict(modules=[row]),r,importer);ck(r['complete']and len(r['modules'])==1,'import_success')
  else:raises(lambda:nw.imports(dict(modules=[row]),r,importer),'import_refused:'+mode)
 with tempfile.TemporaryDirectory()as temp:
  root=Path(temp).resolve();a=nw.audit_for(root)
  for ev,args in [('socket.connect',(None,)),('subprocess.Popen',()),('open',('/tmp/model.safetensors','r',0)),('open',('/tmp/out','w',os.O_WRONLY)),('os.mkdir',('/tmp/cache',0o700,-1))]:raises(lambda:a(ev,args),'audit:'+ev+':'+mode)
  a('open',(str(root/'native_result.json'),'w',os.O_CREAT|os.O_WRONLY));ck(True,'private_output_allowed:'+mode)
# Invoke actual service lifecycle with recorded manager context, fake wire replies,
# real private gate/result files, and simulated /proc/cgroup observations.
for mode in ['success','native_failure','unit_exists','policy_mismatch','ready_mismatch','stop_identity_changed','helper_failure','memory_low']:
 with tempfile.TemporaryDirectory()as temp:
  root=Path(temp).resolve();p=copy.deepcopy(plan);p['root']=str(root);ns.configure(p);pid=2123456789
  state={'status':'none','starts':0,'stops':0,'gate':False};inv=list(range(1,17));ep=actual['transport']['queries'][0]['before'];template=actual['transport']['queries'][0]['result'];manager=actual['rehearsal']['managers'][0]
  ready=dict(pid=pid if mode!='ready_mismatch'else pid-1,attempt_id=p['attempt_id'],plan_binding=p['worker_plan_binding']);(root/'native_ready.json').write_bytes(E(ready))
  def observe(mp,check,r,runner):r.update(copy.deepcopy(manager))
  def endpoint(c,r):r.update(copy.deepcopy(ep))
  def helper(argv,check):
   if mode=='helper_failure':raise ValueError('synthetic helper failure')
   name=argv[len(ns.prefix())+3] # method name
   if name=='StartTransientUnit':state['status']='running';state['starts']+=1;sig='o';value='/org/freedesktop/systemd1/job/100'
   elif name=='StopUnit':state['status']='none';state['stops']+=1;sig='o';value='/org/freedesktop/systemd1/job/101'
   elif name=='ListUnitsByPatterns':
    sig=ns.wire.LIST_SIG
    exists=state['status']!='none'or(mode=='unit_exists'and not state['starts'])
    value=[[ns.wire.UNIT,ns.wire.DESCRIPTION,'loaded','active',state['status']if state['status']!='none'else'running','',ns.unitpath(),0,'','/']]if exists else[]
   elif name=='Get':
    field=argv[-1];policy={n:(s,v)for n,s,v in ns.wire.POLICY};extra={'Id':('s',ns.wire.UNIT),'Transient':('b',True),'InvocationID':('ay',inv if not(mode=='stop_identity_changed'and state['gate'])else[3]*16),'ExecMainPID':('u',pid),'ExecStart':('a(sasbttttuii)',[[ns.wire.EXEC[0],ns.wire.EXEC,False,1,2,3,4,pid,1,0]]),'ControlGroup':('s',ns.wire.GROUP[len('/sys/fs/cgroup'):]),'Result':('s','success'),'ExecMainCode':('i',1),'ExecMainStatus':('i',0)}
    sig,value=extra.get(field,policy.get(field,(None,None)))
    if mode=='policy_mismatch'and field=='MemoryMax':value=1024
    value={'type':sig,'data':value};sig='v'
   else:raise AssertionError(('unexpected',argv))
   out=copy.deepcopy(template);out['argv']=list(argv);out['stdout']=json.dumps(dict(type=sig,data=[value]))+'\n';out['stdout_binding']=H(out['stdout'].encode());out['stderr']='';out['stderr_binding']=H(b'');return out
  def memory(c,r):
   if mode=='memory_low':raise ValueError('host_memory_headroom_24GiB')
   r.update(complete=True,reservation=False)
  def hierarchy(ctx,c,r):r.update(complete=True,errors=[],groups=[dict(values={'cgroup.subtree_control':['memory','pids']})])
  def group(p,c,r):v=dict(path=p['group'],empty=True,absent=True);r.update(complete=True,errors=[],observation=v);return v
  original=ns.file_bytes
  def read(path,cap,c,r,owner=None):
   if path.startswith(str(root)):return original(path,cap,c,r,owner=os.geteuid())
   data={'memory.max':b'21474836480\n','memory.swap.max':b'0\n','pids.max':b'32\n','cmdline':b'\x00'.join(x.encode()for x in ns.wire.EXEC)+b'\x00','cgroup':('0::'+ns.wire.GROUP[len('/sys/fs/cgroup'):]+'\n').encode()}[path.rsplit('/',1)[-1]];r.update(complete=True,errors=[]);return data
  original_write=ns.write_file
  def write(root,name,raw):
   got=original_write(root,name,raw)
   if name=='native_go.json':
    state['gate']=True;state['status']='exited';v=dict(schema='HunyuanCPULoadResult.v1',elapsed_seconds=1,pid=pid,uid=1000,attempt_id=p['attempt_id'],plan_binding=p['worker_plan_binding'],complete=mode!='native_failure',errors=[]if mode!='native_failure'else[{'message':'synthetic import failure'}],model_executed=False,weights_loaded=True,cuda_api_invoked_by_probe=False)
    v['imports_complete']=True
    v['cpu_load']=dict(complete=True,weights_loaded=True,models_constructed=['model','vae','conditioner'],checkpoint_tensors=1645,all_checkpoint_values_finite=True,sources_rechecked_after_load=True,inference_executed=False,explicit_cuda_work=False,groups=p['worker_plan']['cpu_load']['expected_groups'])
    spec=p['worker_plan']['cpu_load'];v['checkpoint_before']=v['checkpoint_after']=dict(path=spec['checkpoint_path'],binding=spec['checkpoint_binding'],identity=[1]*7,route=[['/',1,2,3,0]]);v['checkpoint_fd_closed']=True;v['config_receipt']=dict(path=spec['config_path'],binding=spec['config_binding'])
    v['null_device_open_admissions']=[]
    v['modules']=[dict(module=x['module'],name=x['module'],path=x['path'],returned=True)for x in p['worker_plan']['modules']]
    v['sources_before']=[dict(path=x['path'],binding=x['binding'],identity=[1]*7)for x in p['worker_plan']['modules']]
    v['sources_after']=v['preflight']=v['sources_before']
    v['support_sources_before']=[dict(path=x['path'],binding=x['binding'],identity=[1]*7)for x in p['worker_plan']['support_sources']]
    v['support_sources_after']=v['support_preflight']=v['support_sources_before']
    (root/'native_result.json').write_bytes(E(v))
   return got
  with patch.object(ns,'manager_observe',observe),patch.object(ns,'memory_admission',memory),patch.object(ns,'hierarchy',hierarchy),patch.object(ns,'read_group',group),patch.object(ns,'file_bytes',read),patch.object(ns,'write_file',write),patch.object(ns.time,'sleep',lambda _:None):
   r={};ns.run(p,lambda:None,r,helper,endpoint)
  ck(state['starts']<=1 and state['stops']<=1,'one_attempt:'+mode)
  if mode=='success':ck(r['complete']and r['cleanup_verified']and r['native_imports_passed'],'lifecycle_success:'+str(r['errors']))
  else:ck(not r['complete']and bool(r['errors']),'lifecycle_hold:'+mode)
  if mode in ['success','native_failure','policy_mismatch','ready_mismatch']:ck(state['stops']==1 and r['cleanup_verified'],'cleanup_after:'+mode)
  if mode=='native_failure':ck(r['native_result']['errors']and not r['cpu_load_passed'],'retain_import_failure')
  if mode=='stop_identity_changed':ck(state['stops']==0,'no_stop_on_changed_identity')
  if mode in ['unit_exists','helper_failure','memory_low']:ck(state['starts']==state['stops']==0,'no_start_on_admission_failure:'+mode)
  ck(len(r['transport']['queries'])<=512,'bounded_helpers:'+mode)
  if mode=='success':
   fixture=copy.deepcopy(r);(N/'service_fixture.json').write_bytes(E(fixture))
for field in ['modules','sources_before','preflight','support_sources_before','support_sources_after','support_preflight']:
 bad=copy.deepcopy(fixture['native_result']);bad[field]=[];raises(lambda:ns.validate_result(bad,plan,fixture['identity']),'result_proof:'+field)
# Strict helper allowlist/latches and exact resource policy.
ns.configure(plan);r={};obj=ns.Runner(plan,r);peer=':1.2'
for a in [ns.wire.request(peer),ns.wire.stop_request(peer),ns.wire.list_argv(peer)]:ck(obj.classify(a)in ['start','stop','read'],'allow_exact_command')
for a in [ns.wire.request(peer)[:-1]+['1'],['/bin/sh','-c','true'],ns.wire.stop_request(peer)[:-2]+['other.service','fail']]:raises(lambda:obj.classify(a),'deny_changed_command')
ck(dict((n,v)for n,s,v in ns.wire.POLICY)['MemoryMax']==20*1024**3,'memory_limit');ck(plan['worker_plan']['environment']['CUDA_VISIBLE_DEVICES']=='','gpu_hidden')

# Each mutation is marked before the helper, including a failed helper.
for mode in ['repeat','helper_failure','endpoint_change','cap','reentry']:
 rr={};events=[];ep=copy.deepcopy(actual['transport']['queries'][0]['before']);counter=[0];obj=None
 def endpoint(c,row):
  counter[0]+=1;row.update(copy.deepcopy(ep))
  if mode=='endpoint_change'and counter[0]==2:row['tool']['binding']['sha256']='0'*64
 def helper(argv,c):
  events.append(argv)
  if mode=='helper_failure':raise ValueError('helper failed')
  if mode=='reentry':
   try:obj(argv,c)
   except ValueError:pass
  return {'inert':True}
 obj=ns.Runner(plan,rr,helper,endpoint)
 if mode=='cap':rr['queries']=[{}]*512
 call=lambda:obj(ns.wire.request(':1.2'),lambda:None)
 if mode=='repeat':call();raises(call,'repeat_start_refused')
 else:raises(call,'runner_failure:'+mode)
 raises(call,'persistent_latch:'+mode);ck(len(events)==(0 if mode=='cap'else 1),'no_duplicate_helper:'+mode)
(N/('probe_tests_python'+str(sys.version_info.major)+str(sys.version_info.minor)+'.json')).write_bytes(E(dict(passed=True,count=len(checks),checks=checks,server_contacted=False,native_dependencies_imported=False)));print('PROBE',len(checks))
