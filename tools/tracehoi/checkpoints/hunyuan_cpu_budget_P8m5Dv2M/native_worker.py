"""One CPU construction/strict-loading diagnostic; no inference or explicit CUDA work."""
import errno,hashlib,importlib,json,os,stat,sys,time,traceback
from pathlib import Path
E=lambda x:(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
H=lambda b:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def need(v,n):
 if not v:raise ValueError(n)
def stable(path,binding=None):
 p=Path(path)
 for d in reversed(p.parents):need(stat.S_ISDIR(d.lstat().st_mode),'source_parent_directory')
 a=p.lstat();need(stat.S_ISREG(a.st_mode)and a.st_size<=2*1048576,'source_regular_cap')
 fd=os.open(str(p),os.O_RDONLY|os.O_NOFOLLOW)
 try:
  b=os.fstat(fd);raw=b''
  while True:
   x=os.read(fd,65536);raw+=x;need(len(raw)<=2*1048576,'source_read_cap')
   if not x:break
  k=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
  need(k(a)==k(b)==k(os.fstat(fd))==k(p.lstat()),'source_changed')
 finally:os.close(fd)
 need(binding is None or H(raw)==binding,'source_binding')
 return raw,dict(path=str(p),binding=H(raw),identity=list(k(a)))
def save(path,obj):
 raw=E(obj);need(len(raw)<=1048576,'report_cap')
 fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  pos=0
  while pos<len(raw):n=os.write(fd,raw[pos:]);need(n>0,'write_progress');pos+=n
  os.fsync(fd)
 finally:os.close(fd)
 d=os.open(str(Path(path).parent),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:os.fsync(d)
 finally:os.close(d)
 return H(raw)
def null_device_identity():
 # Only the literal, root-owned Linux null device is eligible; no aliases.
 parent=os.lstat('/dev');value=os.lstat('/dev/null')
 need(stat.S_ISDIR(parent.st_mode)and parent.st_uid==0 and not(parent.st_mode&0o022),'null_parent_identity')
 need(stat.S_ISCHR(value.st_mode)and value.st_uid==0 and os.major(value.st_rdev)==1 and os.minor(value.st_rdev)==3,'null_device_identity')
 return dict(path='/dev/null',device=value.st_dev,inode=value.st_ino,mode=value.st_mode,uid=value.st_uid,rdev=value.st_rdev,major=1,minor=3)
def audit_for(root,admissions=None,denials=None):
 prefix=str(root)+'/'
 if admissions is None:admissions=[]
 if denials is None:denials=[]
 def check_event(event,args):
  # Deny the exact optional fontconfig discovery request with a normal OS error.
  # Matplotlib handles this denial by scanning its ordinary font directories.
  if event=='subprocess.Popen'and len(args)==4 and args[0]=='fc-list'and type(args[1])is list and args[1]==['fc-list','--help']and args[2]is None:
   raise PermissionError(errno.EACCES,'import_probe_forbidden:subprocess.Popen','fc-list')
  # platform._Processor.from_subprocess catches OSError and returns no label.
  # The exact observed uname request stays blocked before a child can start.
  if event=='subprocess.Popen'and len(args)==4 and args[0]=='uname'and type(args[1])is list and args[1]==['uname','-p']and args[2]is None:
   raise PermissionError(errno.EACCES,'import_probe_forbidden:subprocess.Popen','uname')
  if event in {'socket.connect','socket.connect_ex','socket.bind','subprocess.Popen','os.system','os.posix_spawn','os.fork','os.forkpty','os.exec'}:raise RuntimeError('import_probe_forbidden:'+event)
  if event=='open' and isinstance(args[0],(str,bytes)):
   p=os.fsdecode(args[0]);mode=args[1];flags=args[2]
   need(not p.lower().endswith(('.safetensors','.ckpt','.pt','.pth','.bin','.onnx')),'checkpoint_read_forbidden')
   if (type(mode)is str and any(c in mode for c in 'wax+'))or(type(flags)is int and flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)):
    if p=='/dev/null':
     need(len(admissions)<64,'null_admission_cap');identity=null_device_identity()
     need(not admissions or identity==admissions[0]['identity'],'null_device_changed')
     admissions.append(dict(identity=identity,mode=mode,flags=flags));return
    need(p.startswith(prefix)and '..'not in Path(p).parts,'write_outside_private_probe')
  if event in {'os.mkdir','os.remove','os.rmdir','os.rename'}:
   for p in args[:2]if event=='os.rename'else args[:1]:
    if isinstance(p,(str,bytes)):need(os.fsdecode(p).startswith(prefix)and '..'not in Path(os.fsdecode(p)).parts,'mutation_outside_private_probe')
 def audit(event,args):
  try:return check_event(event,args)
  except (ValueError,RuntimeError,PermissionError)as error:
   if len(denials)<16:
    item=dict(event=event,reason=str(error)[:200])
    if args and isinstance(args[0],(str,bytes)):item['path']=os.fsdecode(args[0])[:1000]
    if event=='subprocess.Popen'and len(args)>1 and type(args[1])in (list,tuple):item['argv']=[str(x)[:200]for x in args[1][:16]]
    if isinstance(error,PermissionError):item.update(error_type='PermissionError',errno=error.errno,action='blocked_optional_processor_discovery'if error.filename=='uname'else'blocked_optional_fontconfig_discovery')
    denials.append(item)
   raise
 return audit
def imports(plan,record,importer=importlib.import_module):
 rows=plan['modules'];support=plan.get('support_sources',[]);record.update(modules=[],sources_before=[],sources_after=[],support_sources_before=[],support_sources_after=[],complete=False)
 for row in rows:record['sources_before'].append(stable(row['path'],row['binding'])[1])
 for row in support:record['support_sources_before'].append(stable(row['path'],row['binding'])[1])
 for row in rows:
  item=dict(module=row['module'],returned=False);record['modules'].append(item)
  m=importer(row['module']);item.update(path=getattr(m,'__file__',None),name=getattr(m,'__name__',None))
  need(item['path']==row['path']and item['name']==row['module'],'import_origin')
  item['returned']=True
 for row in rows:record['sources_after'].append(stable(row['path'],row['binding'])[1])
 for row in support:record['support_sources_after'].append(stable(row['path'],row['binding'])[1])
 need(record['support_sources_before']==record['support_sources_after'],'support_source_identity_after_imports')
 need(record['sources_before']==record['sources_after'],'source_identity_after_imports');record['complete']=True

def checkpoint_open(path,binding):
 p=Path(path)
 route=[]
 for parent in reversed(p.parents):
  st=parent.lstat();need(stat.S_ISDIR(st.st_mode),'checkpoint_parent_directory');route.append((str(parent),st.st_dev,st.st_ino,st.st_mode,st.st_uid))
 st=p.lstat();need(stat.S_ISREG(st.st_mode)and st.st_uid==1000 and st.st_size==binding['bytes']and 0<st.st_size<=6*1024**3,'checkpoint_regular_size')
 fd=os.open(str(p),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  proof=checkpoint_hash(fd,p,binding,route);return fd,proof
 except BaseException:os.close(fd);raise

def checkpoint_hash(fd,path,binding,route):
 key=lambda x:[x.st_dev,x.st_ino,x.st_mode,x.st_uid,x.st_size,x.st_mtime_ns,x.st_ctime_ns]
 before=key(os.fstat(fd));need(before==key(os.lstat(path)),'checkpoint_identity')
 os.lseek(fd,0,os.SEEK_SET);h=hashlib.sha256();size=0
 while True:
  block=os.read(fd,min(1048576,binding['bytes']+1-size));size+=len(block);need(size<=binding['bytes'],'checkpoint_growth')
  if not block:break
  h.update(block)
 got=dict(bytes=size,sha256=h.hexdigest());need(got==binding,'checkpoint_hash')
 need(before==key(os.fstat(fd))==key(os.lstat(path)),'checkpoint_changed')
 for name,dev,ino,mode,uid in route:
  st=os.lstat(name);need((st.st_dev,st.st_ino,st.st_mode,st.st_uid)==(dev,ino,mode,uid),'checkpoint_route_changed')
 return dict(path=str(path),binding=got,identity=before,route=route)

def cpu_load(spec,api,record,progress=lambda _:None):
 """Match the reviewed CPU part of build_pipeline, retaining all three components.
 No pipeline, generator, forward pass or GPU transfer is called.
 """
 import copy,math
 torch=api['torch'];expected=spec['expected_schema'];weights={};objects={};actual=None;state=None;obj=None;tensor=None
 record.update(complete=False,groups=[],models_constructed=[],weights_loaded=False,inference_executed=False,explicit_cuda_work=False)
 try:
  progress('load_safetensors_cpu');weights=api['load_file'](spec['load_path'],device='cpu');record['weights_loaded']=True
  need(type(weights)is dict and set(weights)==set(expected),'loaded_keys')
  for name,shape in expected.items():
   tensor=weights[name];need(list(tensor.shape)==shape and tensor.dtype==torch.float16 and tensor.device.type=='cpu','loaded_schema:'+name)
   need(bool(torch.isfinite(tensor).all().item()),'nonfinite_checkpoint:'+name)
  tensor=None;record['checkpoint_tensors']=len(weights);record['all_checkpoint_values_finite']=True
  with torch.no_grad():
   for group in ['model','vae','conditioner']:
    progress('construct:'+group);obj=api[group](**copy.deepcopy(spec['constructors'][group]['params']));objects[group]=obj;record['models_constructed'].append(group)
    want={n[len(group)+1:]:shape for n,shape in expected.items()if n.startswith(group+'.')}
    actual=obj.state_dict();need(set(actual)==set(want)and all(list(actual[n].shape)==shape and actual[n].device.type=='cpu'for n,shape in want.items()),'constructed_schema:'+group);actual=None
    state={n[len(group)+1:]:t for n,t in weights.items()if n.startswith(group+'.')}
    progress('strict_load:'+group);receipt=obj.load_state_dict(state,strict=True);need(not receipt.missing_keys and not receipt.unexpected_keys,'strict_receipt:'+group)
    obj.to(device='cpu',dtype=torch.float16);obj.eval();actual=obj.state_dict()
    need(set(actual)==set(want),'converted_keys:'+group)
    for name in want:
     tensor=actual[name];need(tensor.device.type=='cpu'and tensor.dtype==torch.float16 and list(tensor.shape)==want[name]and torch.equal(tensor,state[name]),'loaded_value_mismatch:'+group+'.'+name)
    record['groups'].append(dict(group=group,tensors=len(want),elements=sum(math.prod(x)for x in want.values()),schema_binding=H(E(want)),strict=True,missing_keys=[],unexpected_keys=[],device='cpu',dtype='float16',all_values_equal=True))
    actual=None;state.clear();state=None;tensor=None;obj=None;receipt=None
    for name in list(weights):
     if name.startswith(group+'.'):del weights[name]
    progress('verified:'+group)
  need(not weights and len(record['groups'])==3,'checkpoint_groups_consumed');record['complete']=True
 finally:
  weights.clear();objects.clear()
  if state is not None:state.clear()
  actual=None;state=None;obj=None;tensor=None


def perform_cpu_load(plan,record,root):
 spec=plan['cpu_load'];progress_count=[0]
 def progress(stage):
  name='cpu_progress_%02d.json'%progress_count[0];progress_count[0]+=1;need(progress_count[0]<=32,'progress_cap')
  save(root/name,dict(stage=stage,attempt_id=plan['attempt_id'],pid=os.getpid(),plan_binding=record['plan_binding'],cpu_load=record.get('cpu_load',{})))
 progress('checkpoint_hash_before')
 fd=None
 try:
  _,record['config_receipt']=stable(spec['config_path'],spec['config_binding'])
  fd,before=checkpoint_open(spec['checkpoint_path'],spec['checkpoint_binding']);record['checkpoint_before']=before
  # Native loader reads this already-held inode; it cannot follow a replaced pathname.
  spec=dict(spec,load_path='/proc/self/fd/'+str(fd))
  torch=sys.modules['torch'];need(torch.get_default_dtype()==torch.float32,'default_float32');torch.set_num_threads(1)
  api=dict(torch=torch,load_file=sys.modules['safetensors.torch'].load_file,
    model=sys.modules['hy3dgen.shapegen.models.hunyuan3ddit'].Hunyuan3DDiT,
    vae=sys.modules['hy3dgen.shapegen.models.vae'].ShapeVAE,
    conditioner=sys.modules['hy3dgen.shapegen.models.conditioner'].SingleImageEncoder)
  record['cpu_load']={};cpu_load(spec,api,record['cpu_load'],progress)
  progress('checkpoint_hash_after');record['checkpoint_after']=checkpoint_hash(fd,spec['checkpoint_path'],spec['checkpoint_binding'],before['route'])
  need(record['checkpoint_before']==record['checkpoint_after'],'checkpoint_receipt_changed')
  need(stable(spec['config_path'],spec['config_binding'])[1]==record['config_receipt'],'config_changed')
  need([stable(x['path'],x['binding'])[1]for x in plan['modules']]==record['sources_before'],'sources_after_load')
  need([stable(x['path'],x['binding'])[1]for x in plan['support_sources']]==record['support_sources_before'],'support_after_load')
  record['cpu_load']['sources_rechecked_after_load']=True;progress('cpu_load_complete')
 finally:
  if fd is not None:os.close(fd);record['checkpoint_fd_closed']=True

def main():
 root=Path(__file__).absolute().parent;record=dict(schema='HunyuanCPULoadResult.v1',attempt_id='P8m5Dv2M',pid=os.getpid(),uid=os.geteuid(),complete=False,errors=[],model_executed=False,weights_loaded=False,cuda_api_invoked_by_probe=False);start=time.monotonic()
 try:
  need(len(sys.argv)==2 and len(sys.argv[1])==64,'plan_argument')
  raw,_=stable(root/'worker_plan.json');need(H(raw)['sha256']==sys.argv[1],'worker_plan_sha');plan=json.loads(raw)
  need(plan['attempt_id']=='P8m5Dv2M'and str(root)==plan['root']and os.geteuid()==1000,'worker_scope')
  stable(__file__,plan['worker_binding']);need(sys.flags.isolated==1 and sys.flags.no_site==1 and sys.dont_write_bytecode,'isolated_worker')
  need(all(os.environ.get(k)==v for k,v in plan['environment'].items()),'worker_environment')
  sys.path[:0]=plan['import_paths'];record['sys_path']=list(sys.path);record['plan_binding']=H(raw)
  # Refuse stale sources before signaling readiness; no captured source is executed.
  record['preflight']=[stable(x['path'],x['binding'])[1]for x in plan['modules']]
  record['support_preflight']=[stable(x['path'],x['binding'])[1]for x in plan.get('support_sources',[])]
  save(root/'native_ready.json',dict(pid=os.getpid(),attempt_id=plan['attempt_id'],plan_binding=H(raw)))
  for _ in range(200):
   try:gate,_=stable(root/'native_go.json')
   except FileNotFoundError:time.sleep(.1);continue
   need(json.loads(gate)==dict(pid=os.getpid(),plan_binding=H(raw)),'native_gate');break
  else:raise ValueError('native_gate_deadline')
  import resource
  resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(1048576,1048576))
  record['null_device_open_admissions']=[]
  record['audit_denials']=[]
  sys.addaudithook(audit_for(root,record['null_device_open_admissions'],record['audit_denials']));imports(plan,record)
  record['imports_complete']=True;record['complete']=False;perform_cpu_load(plan,record,root);record['complete']=True
 except BaseException as e:
  record['complete']=False;record['errors'].append(dict(type=type(e).__name__,message=str(e)[:1000],traceback=traceback.format_exc()[-6000:]))
 record['weights_loaded']=record.get('cpu_load',{}).get('weights_loaded',False)
 record['elapsed_seconds']=time.monotonic()-start;save(root/'native_result.json',record)
 # Zero means the diagnostic saved its result. Parent separately evaluates imports.
 return 0
if __name__=='__main__':raise SystemExit(main())
