"""One bounded CPU load worker. Exact Start/StopUnit only; no inference or holder."""
import copy,json,os,re,time,stat
from pathlib import Path
from read_helpers import E,H,need,prefix,file_bytes,socket_snapshot,run_helper
from manager_observation import observe as manager_observe,helper_value,argv_for
from cgroup_admission import hierarchy,compare_managers
from cgroup_readers import read_group
from probe_storage import write_file
import service_protocol as wire

def configure(plan):
 wire.DESCRIPTION='TraceHOI CPU strict-load diagnostic P8m5Dv2M'
 wire.EXEC=[plan['interpreter']['path'],'-I','-S','-B',plan['root']+'/native_worker.py',plan['worker_plan_binding']['sha256']]
 changes={'Description':wire.DESCRIPTION,'RuntimeMaxUSec':300000000,'MemoryMax':20*1024**3,'TasksMax':32,'Environment':[k+'='+v for k,v in sorted(plan['worker_plan']['environment'].items())]}
 wire.POLICY=[(n,s,changes.get(n,v))for n,s,v in wire.POLICY]
 if not any(n=='MemorySwapMax'for n,_,_ in wire.POLICY):wire.POLICY.append(('MemorySwapMax','t',0))
 # Include inheritance-sensitive variables from the previous worker policy.
 unset=next(v for n,s,v in wire.POLICY if n=='UnsetEnvironment')
 for n in ['PYTHONPATH','PYTHONHOME','PYTHONSTARTUP','PYTHONINSPECT']:
  if n not in unset:unset.append(n)

def endpoint(check,record):
 record.update(tool={},socket={});file_bytes('/usr/bin/busctl',2*1048576,check,record['tool'],owner=0,executable=True);socket_snapshot(1000,check,record['socket']);return record

def epkey(row):
 for k in ['tool','socket']:need(row[k].get('complete')is True and row[k].get('errors')==[],'endpoint_complete')
 return {k:{x:row[k][x]for x in (['binding','before','route']if k=='tool'else['before','route'])}for k in ['tool','socket']}

def unitpath():return '/org/freedesktop/systemd1/unit/'+''.join(c if c.isascii()and c.isalnum()else '_'+format(ord(c),'02x')for c in wire.UNIT)

class Runner:
 def __init__(self,plan,record,helper=run_helper,reader=endpoint):
  self.plan=plan;self.r=record;self.helper=helper;self.reader=reader;self.active=False;self.failed=False;self.mutations=set();self.baseline=None
  record.update(queries=[],complete=False,errors=[])
 def classify(self,argv):
  need(type(argv)is list and all(type(x)is str for x in argv),'argv_type')
  if argv in [argv_for('bus_id'),argv_for('owner')]:return 'read'
  need(argv[:len(prefix())]==prefix()and len(argv)>len(prefix()),'helper_prefix')
  for peer in [argv[-1],argv[len(prefix())]]:
   if not re.fullmatch(r':[0-9]+\.[0-9]+',peer):continue
   for name in ['uid','pid','Version','Features']:
    if argv==argv_for(name,peer):return 'read'
   if argv==wire.request(peer):return 'start'
   if argv==wire.stop_request(peer):return 'stop'
   if argv==wire.list_argv(peer):return 'read'
   for name in set(n for n,_,_ in wire.POLICY)|{'Id','Transient','ControlGroup','InvocationID','ExecMainPID','ExecStart','ActiveState','SubState','Result','ExecMainCode','ExecMainStatus'}:
    if argv==wire.property_argv(peer,unitpath(),name):return 'read'
  raise ValueError('unlisted_helper_command')
 def __call__(self,argv,check):
  if self.active or self.failed:self.failed=True;raise ValueError('runner_latched')
  self.active=True
  try:
   check();kind=self.classify(argv);need(len(self.r['queries'])<512,'manager_call_cap')
   if kind!='read':need(kind not in self.mutations,'single_mutation');self.mutations.add(kind)
   row=dict(argv=list(argv),kind=kind,before={},after={},attempted=False,result=None,complete=False);self.r['queries'].append(row)
   self.reader(check,row['before']);key=epkey(row['before']);need(key['tool']['binding']==self.plan['manager_plan']['tool_binding'],'busctl_pin')
   if self.baseline is None:self.baseline=key
   need(key==self.baseline,'endpoint_before');row['attempted']=True
   try:row['result']=copy.deepcopy(self.helper(argv,check))
   except BaseException as e:row['result']=copy.deepcopy(getattr(e,'helper_record',None));raise
   self.reader(check,row['after']);need(epkey(row['after'])==self.baseline and not self.failed,'endpoint_after');row['complete']=True;return copy.deepcopy(row['result'])
  except BaseException as e:self.failed=True;self.r['errors'].append(dict(type=type(e).__name__,message=str(e)[:300]));raise
  finally:self.active=False

def identity(values,expected=None):
 need(values['Id']==wire.UNIT and values['Transient']is True,'unit_identity')
 inv=values['InvocationID'];pid=values['ExecMainPID'];cmd=values['ExecStart']
 need(type(inv)is list and len(inv)==16 and all(type(x)is int and 0<=x<=255 for x in inv)and any(inv),'unit_invocation')
 need(type(pid)is int and pid>1 and len(cmd)==1 and cmd[0][:3]==[wire.EXEC[0],wire.EXEC,False]and cmd[0][7]==pid,'unit_exec_identity')
 result=dict(invocation=inv,pid=pid,command=cmd[0][:3])
 need(expected is None or result==expected,'unit_identity_changed');return result

def validate_result(result,plan,ident):
 need(result.get('schema')=='HunyuanCPULoadResult.v1'and result.get('pid')==ident['pid']and result.get('uid')==1000 and result.get('attempt_id')==plan['attempt_id']and result.get('plan_binding')==plan['worker_plan_binding'],'native_result_identity')
 need(all(result.get(k)is False for k in ['model_executed','cuda_api_invoked_by_probe']),'import_only_scope')
 if not(result.get('complete')is True and result.get('errors')==[]):return False
 admissions=result.get('null_device_open_admissions');need(type(admissions)is list and len(admissions)<=64,'null_admissions')
 for row in admissions:
  dev=row['identity'];need(dev==admissions[0]['identity']and dev['path']=='/dev/null'and dev['uid']==0 and stat.S_ISCHR(dev['mode'])and dev['major']==1 and dev['minor']==3,'null_admission_identity')
 modules=plan['worker_plan']['modules']
 need(result.get('modules')==[dict(module=x['module'],name=x['module'],path=x['path'],returned=True)for x in modules],'complete_import_list')
 before=result.get('sources_before');need(type(before)is list and len(before)==len(modules)and before==result.get('sources_after')==result.get('preflight'),'stable_native_sources')
 for want,got in zip(modules,before):need(got['path']==want['path']and got['binding']==want['binding']and type(got['identity'])is list and len(got['identity'])==7,'native_source_evidence')
 support=plan['worker_plan'].get('support_sources',[])
 support_before=result.get('support_sources_before')
 need(type(support_before)is list and len(support_before)==len(support)and support_before==result.get('support_sources_after')==result.get('support_preflight'),'stable_support_sources')
 for want,got in zip(support,support_before):need(got['path']==want['path']and got['binding']==want['binding']and type(got['identity'])is list and len(got['identity'])==7,'support_source_evidence')
 need(type(result.get('elapsed_seconds'))in (int,float)and 0<=result['elapsed_seconds']<300,'native_elapsed')
 load=result.get('cpu_load',{});need(type(load)is dict,'cpu_load_record');need(load.get('complete')is True and load.get('weights_loaded')is True and load.get('models_constructed')==['model','vae','conditioner']and load.get('checkpoint_tensors')==1645 and load.get('all_checkpoint_values_finite')is True and load.get('sources_rechecked_after_load')is True,'cpu_load_complete')
 need(load.get('inference_executed')is False and load.get('explicit_cuda_work')is False and result.get('weights_loaded')is True and result.get('imports_complete')is True,'cpu_load_scope')
 spec=plan['worker_plan']['cpu_load'];expected=spec['expected_groups'];need(load.get('groups')==expected,'cpu_load_groups')
 a=result.get('checkpoint_before');need(type(a)is dict and a==result.get('checkpoint_after')and a.get('path')==spec['checkpoint_path']and a.get('binding')==spec['checkpoint_binding']and type(a.get('identity'))is list and len(a['identity'])==7 and a.get('route')and result.get('checkpoint_fd_closed')is True,'checkpoint_proof')
 config=result.get('config_receipt',{});need(type(config)is dict,'config_record');need(config.get('path')==spec['config_path']and config.get('binding')==spec['config_binding'],'config_proof')
 return True

def memory_admission(check,record):
 row={};record['host']=row;raw=file_bytes('/proc/meminfo',65536,check,row);row['text']=raw.decode();rows=[x for x in raw.decode().splitlines()if x.startswith('MemAvailable:')]
 need(len(rows)==1 and re.fullmatch(r'MemAvailable:\s+[0-9]+ kB',rows[0]),'host_memory_format');available=int(rows[0].split()[1])*1024;record['host_available_bytes']=available
 need(available>=24*1024**3,'host_memory_headroom_24GiB')
 record['ancestors']=[]
 p=Path(wire.GROUP).parent
 while str(p).startswith('/sys/fs/cgroup/'):
  item=dict(path=str(p),observations={});record['ancestors'].append(item);values={}
  for name in ['memory.max','memory.current']:
   proof={};item['observations'][name]=proof;values[name]=file_bytes(str(p/name),128,check,proof).decode().strip()
  need(values['memory.current'].isdigit()and(values['memory.max']=='max'or values['memory.max'].isdigit()),'ancestor_memory_format')
  item['values']=values
  if values['memory.max']!='max':need(int(values['memory.max'])-int(values['memory.current'])>=20*1024**3,'ancestor_memory_headroom_20GiB')
  p=p.parent
 record['complete']=True;record['reservation']=False

def run(plan,check,record,helper=run_helper,endpoint_reader=endpoint):
 configure(plan);root=Path(plan['root']);r=record;r.update(complete=False,errors=[],managers=[],transport={},groups=[],properties=[],reads=[],writes=[],native_result=None,cleanup_verified=False,service_submitted=False,submission_attempted=False,stop_attempted=False,stop_request_accepted=False,native_imports_passed=False,cpu_load_passed=False,model_executed=False)
 runner=Runner(plan,r['transport'],helper,endpoint_reader);peer=None;ident=None
 def mread():
  row={};r['managers'].append(row);manager_observe(plan['manager_plan'],check,row,runner);return row
 def call(argv,sig='s',variant=False):
  got=runner(argv,check);return wire.list_reply(got,argv)if sig==wire.LIST_SIG else helper_value(got,argv,sig,variant)
 def listing():return call(wire.list_argv(peer),wire.LIST_SIG)
 def prop(n,s):return call(wire.property_argv(peer,unitpath(),n),s,True)
 def properties():
  x={};r['properties'].append(x)
  for n,s in [('Id','s'),('Transient','b'),('InvocationID','ay'),('ExecMainPID','u'),('ExecStart','a(sasbttttuii)')]:x[n]=prop(n,s)
  return x
 def group(absent):
  row={};r['groups'].append(row);v=read_group(dict(group=wire.GROUP),check,row);need(v['empty']and(not absent or v['absent']),'worker_group_not_empty');return v
 def read(name,cap=1048576):
  row={};r['reads'].append(row);raw=file_bytes(str(root/name),cap,check,row,owner=1000);row['text']=raw.decode();return json.loads(raw)
 try:
  first=mread();peer=first['owners'][0]['unique_name'];ctx=first['processes'][0]['identity']['context'];r['hierarchy']={};hierarchy(ctx,check,r['hierarchy'])
  need(all({'memory','pids'}<=set(x['values']['cgroup.subtree_control'])for x in r['hierarchy']['groups']),'resource_controllers')
  group(True);need(listing()==[],'fresh_unit_required')
  r['memory_admission']={};memory_admission(check,r['memory_admission'])
  r['submission_attempted']=True;r['start_job']=call(wire.request(peer),'o');r['service_submitted']=True
  need(re.fullmatch('/org/freedesktop/systemd1/job/[0-9]+',r['start_job']),'start_job')
  for _ in range(12):
   rows=listing()
   if rows and rows[0][3]in ['active','failed']:break
   time.sleep(.25);check()
  else:raise ValueError('start_deadline')
  ident=identity(properties());r['identity']=copy.deepcopy(ident)
  observed={};r['policy']=observed
  for n,s,want in wire.POLICY:
   got=prop(n,s);observed[n]=got;need(sorted(got)==sorted(want)if s=='as'else got==want,'service_policy:'+n)
  need(prop('ControlGroup','s')==wire.GROUP[len('/sys/fs/cgroup'):],'service_group')
  for _ in range(40):
   try:ready=read('native_ready.json');break
   except FileNotFoundError:time.sleep(.25);check()
  else:raise ValueError('ready_deadline')
  need(ready==dict(pid=ident['pid'],attempt_id=plan['attempt_id'],plan_binding=plan['worker_plan_binding']),'ready_identity')
  kernel={};r['kernel']=kernel
  for path,want in [(wire.GROUP+'/memory.max',b'21474836480\n'),(wire.GROUP+'/memory.swap.max',b'0\n'),(wire.GROUP+'/pids.max',b'32\n'),('/proc/'+str(ident['pid'])+'/cmdline',b'\x00'.join(x.encode()for x in wire.EXEC)+b'\x00')]:
   row={};kernel[path]=row;need(file_bytes(path,8192,check,row)==want,'kernel_limit_or_command');row['text']=want.decode()
  membership={};kernel['membership']=membership;raw=file_bytes('/proc/'+str(ident['pid'])+'/cgroup',4096,check,membership);need(raw==('0::'+wire.GROUP[len('/sys/fs/cgroup'):]+'\n').encode(),'worker_membership');membership['text']=raw.decode()
  identity(properties(),ident)
  r['writes'].append(write_file(root,'native_go.json',E(dict(pid=ident['pid'],plan_binding=plan['worker_plan_binding']))))
  terminal=False
  for _ in range(310):
   rows=listing();need(len(rows)==1 and rows[0][6]==unitpath(),'worker_disappeared_before_capture')
   if rows[0][3]=='failed'or rows[0][3:5]==['active','exited']:terminal=True;break
   need(rows[0][3:5]==['active','running'],'unexpected_worker_state');time.sleep(1);check()
  need(terminal,'cpu_load_completion_deadline');identity(properties(),ident)
  r['exit']={n:prop(n,s)for n,s in [('Result','s'),('ExecMainCode','i'),('ExecMainStatus','i')]}
  need(r['exit']==dict(Result='success',ExecMainCode=1,ExecMainStatus=0),'diagnostic_worker_exit')
  result=read('native_result.json');r['native_result']=result
  r['cpu_load_passed']=validate_result(result,plan,ident);r['native_imports_passed']=result.get('imports_complete',False)
  if not r['cpu_load_passed']:r['errors'].append(dict(type='CPULoadFailure',message='See native_result.errors, cpu_load and cpu_progress records.'))
 except BaseException as e:r['errors'].append(dict(type=type(e).__name__,message=str(e)[:500]))
 finally:
  if ident is not None and not runner.failed:
   try:
    current=mread();compare_managers(r['managers'][0],current);identity(properties(),ident)
    r['stop_attempted']=True;r['stop_job']=call(wire.stop_request(peer),'o');r['stop_request_accepted']=True
    need(re.fullmatch('/org/freedesktop/systemd1/job/[0-9]+',r['stop_job']),'stop_job')
    for _ in range(16):
     if listing()==[]:break
     time.sleep(.5);check()
    else:raise ValueError('stop_collection_deadline')
    group(True);need(listing()==[],'worker_reappeared');group(True)
    for _ in range(2):need(not os.path.lexists('/proc/'+str(ident['pid'])),'worker_pid_present_or_reused')
    r['cleanup_verified']=True
   except BaseException as e:r['errors'].append(dict(stage='cleanup',type=type(e).__name__,message=str(e)[:500]))
  if r['native_result']is None:
   try:r['native_result']=read('native_result.json')
   except (FileNotFoundError,ValueError):pass
  r['transport']['complete']=not runner.failed
 r['complete']=r['cleanup_verified']and r['cpu_load_passed']and not r['errors'];return r
