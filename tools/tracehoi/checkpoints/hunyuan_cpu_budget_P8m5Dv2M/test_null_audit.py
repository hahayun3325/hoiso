from pathlib import Path
import copy,json,os,stat,subprocess,sys,tempfile,types
from unittest.mock import patch
import native_worker as nw,native_service as ns
from read_helpers import E
N=Path(__file__).resolve().parent;checks=[]
def ck(v,n):
 if not v:raise AssertionError(n)
 checks.append(n)
def denied(fn,n):
 try:fn()
 except (ValueError,RuntimeError):ck(True,n)
 else:raise AssertionError(n)

parent=types.SimpleNamespace(st_mode=stat.S_IFDIR|0o755,st_uid=0)
device=types.SimpleNamespace(st_mode=stat.S_IFCHR|0o666,st_uid=0,st_dev=7,st_ino=9,st_rdev=259)
for mode in ['good','symlink','regular','wrong_owner','wrong_major','wrong_minor','parent_symlink','parent_owner','parent_write']:
 d=copy.copy(device);p=copy.copy(parent);major=1;minor=3
 if mode=='symlink':d.st_mode=stat.S_IFLNK|0o777
 if mode=='regular':d.st_mode=stat.S_IFREG|0o666
 if mode=='wrong_owner':d.st_uid=1000
 if mode=='wrong_major':major=2
 if mode=='wrong_minor':minor=5
 if mode=='parent_symlink':p.st_mode=stat.S_IFLNK|0o777
 if mode=='parent_owner':p.st_uid=1000
 if mode=='parent_write':p.st_mode|=0o020
 with patch.object(nw.os,'lstat',lambda path:p if path=='/dev'else d),patch.object(nw.os,'major',lambda _:major),patch.object(nw.os,'minor',lambda _:minor):
  if mode=='good':good=nw.null_device_identity();ck(good['path']=='/dev/null'and good['major']==1 and good['minor']==3,'exact_linux_null')
  else:denied(nw.null_device_identity,'identity_rejected:'+mode)

with tempfile.TemporaryDirectory()as temp:
 root=Path(temp).resolve();admissions=[];audit=nw.audit_for(root,admissions)
 with patch.object(nw,'null_device_identity',lambda:copy.deepcopy(good)):
  for mode,flags in [('r+',os.O_RDWR),('w',os.O_WRONLY|os.O_TRUNC),('a',os.O_WRONLY|os.O_APPEND)]:
   audit('open',('/dev/null',mode,flags));ck(admissions[-1]['identity']==good,'admitted_exact_null:'+mode)
  for path in ['/dev/zero','/dev/random','/dev/null.other','/dev/../tmp/file','/tmp/null','/tmp/shared-result']:
   denied(lambda:audit('open',(path,'r+',os.O_RDWR)),'outside_write_rejected:'+path)
  for event,args in [('os.remove',('/dev/null',-1)),('os.rename',('/dev/null','/tmp/moved',-1,-1)),('os.mkdir',('/dev/null',0o700,-1)),('subprocess.Popen',()),('socket.connect',())]:
   denied(lambda:audit(event,args),'unchanged_restriction:'+event)
  audit('open',(str(root/'result.json'),'w',os.O_CREAT|os.O_WRONLY));ck(len(admissions)==3,'private_write_does_not_consume_null_cap')
  while len(admissions)<64:audit('open',('/dev/null','r+',os.O_RDWR))
  denied(lambda:audit('open',('/dev/null','r+',os.O_RDWR)),'null_cap_64')
 with patch.object(nw,'null_device_identity',lambda:{**good,'inode':10}):
  a=nw.audit_for(root,[dict(identity=good,mode='r+',flags=os.O_RDWR)]);denied(lambda:a('open',('/dev/null','r+',os.O_RDWR)),'changed_device_rejected')
 # A real local open reproduces dill's file-type operation. Linux device
 # identity is injected only in this macOS fixture, without importing dill.
 child='''import os,sys
sys.path.insert(0,SOURCE)
import native_worker as nw
nw.null_device_identity=lambda:IDENTITY
events=[]
sys.addaudithook(nw.audit_for(ROOT,events))
with open(os.devnull,'r+b',buffering=-1)as f:
 assert f.write(b'fixture')==7
assert len(events)==1 and events[0]['identity']==IDENTITY
'''
 code='SOURCE='+repr(str(N))+'\nIDENTITY='+repr(good)+'\nROOT='+repr(str(root))+'\n'+child
 result=subprocess.run([sys.executable,'-I','-S','-B','-c',code],capture_output=True,timeout=10)
 ck(result.returncode==0,'real_null_open_with_fixture_identity:'+result.stderr.decode()[-200:])

plan=json.loads((N/'review_plan.json').read_bytes());fixture=json.loads((N/'service_fixture.json').read_bytes());result=copy.deepcopy(fixture['native_result'])
result['null_device_open_admissions']=[dict(identity=good,mode='r+',flags=os.O_RDWR)]
ck(ns.validate_result(result,plan,fixture['identity']),'parent_accepts_null_record')
for name,value in [('path','/dev/zero'),('uid',1000),('mode',stat.S_IFREG|0o666),('major',2),('minor',5)]:
 bad=copy.deepcopy(result);bad['null_device_open_admissions'][0]['identity'][name]=value
 denied(lambda:ns.validate_result(bad,plan,fixture['identity']),'parent_rejects:'+name)
for mode in ['missing','oversize','changed']:
 bad=copy.deepcopy(result)
 if mode=='missing':bad.pop('null_device_open_admissions')
 if mode=='oversize':bad['null_device_open_admissions']*=65
 if mode=='changed':bad['null_device_open_admissions'].append(dict(identity={**good,'inode':10},mode='r+',flags=os.O_RDWR))
 denied(lambda:ns.validate_result(bad,plan,fixture['identity']),'parent_record_rejected:'+mode)
(N/('null_audit_tests_python'+str(sys.version_info.major)+str(sys.version_info.minor)+'.json')).write_bytes(E(dict(passed=True,count=len(checks),checks=checks,server_contacted=False,native_dependencies_imported=False,linux_device_identity_simulated=True)))
print('NULL_AUDIT',len(checks))
