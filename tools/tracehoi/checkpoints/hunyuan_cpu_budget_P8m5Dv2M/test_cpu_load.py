from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import copy,hashlib,json,os,sys,tempfile,contextlib,stat
import native_worker as nw,native_service as ns
from read_helpers import E,H
N=Path(__file__).resolve().parent;plan=json.loads((N/'review_plan.json').read_bytes());checks=[]
def ck(v,n):
 if not v:raise AssertionError(n)
 checks.append(n)
def rejects(fn,n):
 try:fn()
 except (ValueError,RuntimeError,OSError):ck(True,n)
 else:raise AssertionError(n)
class Tensor:
 def __init__(self,shape,value=3,dtype='half',device='cpu',finite=True):self.shape=shape;self.value=value;self.dtype=dtype;self.device=NS(type=device);self.finite=finite
class Truth:
 def __init__(self,v):self.v=v
 def all(self):return self
 def item(self):return self.v
for mode in ['success','missing_checkpoint_key','wrong_shape','wrong_dtype','wrong_device','nonfinite','constructor_raises','constructor_schema','strict_missing','converted_value','converted_device']:
 stages=[];calls=[];spec=dict(load_path='/proc/self/fd/5',expected_schema={g+'.w':[2]for g in ['model','vae','conditioner']},constructors={g:dict(params={})for g in ['model','vae','conditioner']})
 weights={n:Tensor(shape)for n,shape in spec['expected_schema'].items()}
 if mode=='missing_checkpoint_key':weights.pop('vae.w')
 if mode=='wrong_shape':weights['model.w'].shape=[3]
 if mode=='wrong_dtype':weights['model.w'].dtype='float'
 if mode=='wrong_device':weights['model.w'].device.type='cuda'
 if mode=='nonfinite':weights['model.w'].finite=False
 def load(path,device):ck(path==spec['load_path']and device=='cpu','cpu_load_call:'+mode);return dict(weights)
 class Model:
  def __init__(self,group):
   calls.append('construct:'+group);self.group=group;self.values={'w':Tensor([2],dtype='float')}
   if mode=='constructor_raises':raise RuntimeError('constructor')
   if mode=='constructor_schema':self.values={'wrong':Tensor([2])}
  def state_dict(self):return self.values.copy()
  def load_state_dict(self,state,strict):
   ck(strict is True,'strict:'+mode+':'+self.group);self.values={k:Tensor(v.shape,v.value,dtype='float')for k,v in state.items()};return NS(missing_keys=['x']if mode=='strict_missing'else[],unexpected_keys=[])
  def to(self,device,dtype):
   ck(device=='cpu'and dtype=='half','cpu_conversion:'+mode+':'+self.group)
   for v in self.values.values():
    v.dtype=dtype;v.device.type='cuda'if mode=='converted_device'else device
    if mode=='converted_value':v.value=4
   return self
  def eval(self):return self
 torch=NS(float16='half',no_grad=contextlib.nullcontext,isfinite=lambda x:Truth(x.finite),equal=lambda a,b:a.value==b.value)
 api=dict(torch=torch,load_file=load,**{g:(lambda group=g:Model(group))for g in ['model','vae','conditioner']});r={}
 if mode=='success':
  nw.cpu_load(spec,api,r,stages.append);ck(r['complete']and r['checkpoint_tensors']==3 and len(r['groups'])==3 and r['all_checkpoint_values_finite'],'complete_three_groups');ck(stages==['load_safetensors_cpu']+[s+g for g in ['model','vae','conditioner']for s in ['construct:','strict_load:','verified:']],'ordered_stages')
 else:rejects(lambda:nw.cpu_load(spec,api,r,stages.append),'failure:'+mode);ck(not r['complete'],'no_acceptance:'+mode)
 ck(len(calls)<=3 and len(stages)<=10,'bounded:'+mode)
 if mode in ['missing_checkpoint_key','wrong_shape','wrong_dtype','wrong_device','nonfinite']:ck(not calls,'no_construction_on_bad_checkpoint:'+mode)
# Streamed hashing: real local files, held inode, corruption, symlink and metadata changes.
with tempfile.TemporaryDirectory()as tmp:
 root=Path(tmp).resolve();f=root/'blob';f.write_bytes(b'abcd'*300000);binding=H(f.read_bytes());fd=os.open(str(f),os.O_RDONLY);route=[]
 try:
  a=nw.checkpoint_hash(fd,f,binding,route);ck(a['binding']==binding,'full_stream_hash');ck(nw.checkpoint_hash(fd,f,binding,route)==a,'repeated_stable_hash')
  rejects(lambda:nw.checkpoint_hash(fd,f,dict(binding,sha256='0'*64),route),'bad_hash')
  old=root/'old';f.rename(old);f.write_bytes(old.read_bytes());rejects(lambda:nw.checkpoint_hash(fd,f,binding,route),'replaced_path_held_fd')
 finally:os.close(fd)
 f.unlink();f.symlink_to(old);rejects(lambda:nw.checkpoint_open(f,binding),'symlink_checkpoint_rejected')
# Parent refusal occurs before a new Start request; non-reserving headroom from host and ancestors.
for mode in ['pass','host_low','ancestor_low','bad_format']:
 def reader(path,cap,check,row):
  row.update(complete=True)
  if path=='/proc/meminfo':return (('MemAvailable: %d kB\n'%((23 if mode=='host_low'else 24)*1024**2))if mode!='bad_format'else'MemAvailable: unknown\n').encode()
  if path.endswith('memory.max'):return str(20*1024**3 if mode=='ancestor_low'else 30*1024**3).encode()
  return str(1024**3).encode()
 with patch.object(ns,'file_bytes',reader):
  r={}
  if mode=='pass':ns.memory_admission(lambda:None,r);ck(r['complete']and not r['reservation']and len(r['ancestors'])>0,'memory_pass')
  else:rejects(lambda:ns.memory_admission(lambda:None,r),'memory_refuse:'+mode)
# Parent rejects forged acceptance even if imports passed.
fixture=json.loads((N/'service_fixture.json').read_bytes());base=fixture['native_result'];ident=fixture['identity']
for field in ['complete','weights_loaded','all_checkpoint_values_finite','sources_rechecked_after_load']:
 bad=copy.deepcopy(base);bad['cpu_load'][field]=False;rejects(lambda:ns.validate_result(bad,plan,ident),'reject_cpu_proof:'+field)
for field in ['checkpoint_after','config_receipt','checkpoint_fd_closed']:
 bad=copy.deepcopy(base);bad[field]=None;rejects(lambda:ns.validate_result(bad,plan,ident),'reject_file_proof:'+field)
bad=copy.deepcopy(base);bad['cpu_load']['groups'][0]['all_values_equal']=False;rejects(lambda:ns.validate_result(bad,plan,ident),'reject_value_proof')
ns.configure(plan);policy={n:v for n,_,v in ns.wire.POLICY};ck(policy['RuntimeMaxUSec']==300000000 and policy['MemoryMax']==20*1024**3 and policy['MemorySwapMax']==0 and policy['TasksMax']==32,'service_resource_caps');ck(policy['Restart']=='no'and policy['KillMode']=='control-group','no_restart_group_stop')
ck('torch'not in sys.modules and 'safetensors'not in sys.modules,'no_native_imports_in_tests')
(N/('cpu_load_tests_python'+str(sys.version_info.major)+str(sys.version_info.minor)+'.json')).write_bytes(E(dict(passed=True,count=len(checks),checks=checks)));print('CPU_LOAD',len(checks))
