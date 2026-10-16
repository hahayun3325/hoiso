from pathlib import Path
import json,os,subprocess,sys,tempfile
import native_worker as nw,native_service as ns
from read_helpers import E,H
N=Path(__file__).resolve().parent;checks=[]
def ck(v,n):
 if not v:raise AssertionError(n)
 checks.append(n)
source=N.parent/'model_worker_font_source_return_20261009/packet/source__matplotlib_init.py.txt'
ck(H(source.read_bytes())==dict(bytes=55823,sha256='c6c47d1ecf25d7934f38c8a55c3b8e116d41aa08d8ecfa82f6ae8af589216a3a'),'captured_matplotlib_source_pin')
plan=json.loads((N/'review_plan.json').read_bytes());env=plan['worker_plan']['environment'];root=plan['root']
expected=dict(XDG_CONFIG_HOME=root+'/config',MPLCONFIGDIR=root+'/config/matplotlib',MATPLOTLIBRC=root+'/config/matplotlib',MPLBACKEND='Agg')
for key,value in expected.items():ck(env[key]==value,'private_environment:'+key)
ns.configure(plan);wireenv=dict((n,v)for n,s,v in ns.wire.POLICY)['Environment']
ck(all(k+'='+v in wireenv for k,v in expected.items()),'service_propagates_configuration')
ck(env['HOME']=='/home/fredcui','home_preserved')
for mode in ['old_default','private_explicit','private_xdg']:
 with tempfile.TemporaryDirectory()as temp:
  temp=Path(temp).resolve();target=temp/'attempt';target.mkdir(mode=0o700);outside=temp/'home';outside.mkdir()
  code='''import ast,atexit,json,os,shutil,sys,tempfile,types
from pathlib import Path
sys.path.insert(0,MODULES)
import native_worker as nw
os.umask(0o077)
os.environ['HOME']=OUTSIDE
for key in ['XDG_CONFIG_HOME','MPLCONFIGDIR']:os.environ.pop(key,None)
if MODE!='old_default':os.environ['XDG_CONFIG_HOME']=ROOT+'/config'
if MODE=='private_explicit':os.environ['MPLCONFIGDIR']=ROOT+'/config/matplotlib'
tree=ast.parse(Path(SOURCE).read_text())
names={'_get_xdg_config_dir','_get_xdg_cache_dir','_get_config_or_cache_dir','get_configdir','get_cachedir'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in names]
assert len(nodes)==5
for n in nodes:n.decorator_list=[]
scope=dict(os=os,sys=types.SimpleNamespace(platform='linux'),Path=Path,tempfile=tempfile,atexit=atexit,shutil=shutil,_log=types.SimpleNamespace(warning=lambda *args:None))
exec(compile(ast.Module(body=nodes,type_ignores=[]),SOURCE,'exec'),scope)
denials=[]
sys.addaudithook(nw.audit_for(ROOT,denials=denials))
try:
 chosen=scope['get_configdir']()
 if MODE=='old_default':raise AssertionError('old path accepted')
 assert chosen==ROOT+'/config/matplotlib'
 assert scope['get_configdir']()==chosen
 assert Path(chosen).is_dir()and Path(chosen).stat().st_mode&0o777==0o700
 if MODE=='private_explicit':assert scope['get_cachedir']()==chosen
 with open(Path(chosen)/'fixture.json','w')as f:f.write('{}')
 assert denials==[]
 print(json.dumps(dict(passed=True,result='private_config_created')))
except ValueError as e:
 assert MODE=='old_default'and str(e)=='mutation_outside_private_probe'
 assert denials==[dict(event='os.mkdir',reason='mutation_outside_private_probe',path=OUTSIDE+'/.config/matplotlib')]
 print(json.dumps(dict(passed=True,result='old_default_reproduced')))
'''
  values=dict(MODULES=str(N),OUTSIDE=str(outside),ROOT=str(target),MODE=mode,SOURCE=str(source))
  script=''.join(k+'='+repr(v)+'\n'for k,v in values.items())+code
  done=subprocess.run([sys.executable,'-I','-S','-B','-c',script],capture_output=True,timeout=10)
  ck(done.returncode==0,'captured_configuration_function:'+mode+':'+done.stderr.decode()[-400:])
  ck(json.loads(done.stdout)['passed'],'configuration_result:'+mode)
  ck(not(outside/'.config').exists(),'outside_configuration_untouched:'+mode)
with tempfile.TemporaryDirectory()as temp:
 denials=[];audit=nw.audit_for(Path(temp),denials=denials)
 for i in range(20):
  try:audit('open',('/outside/file'+str(i),'w',os.O_WRONLY))
  except ValueError:pass
  else:raise AssertionError('outside write admitted')
 ck(len(denials)==16,'bounded_denial_records')
 ck(denials[0]==dict(event='open',reason='write_outside_private_probe',path='/outside/file0'),'denial_path_and_reason')
 more=[];audit=nw.audit_for(Path(temp),denials=more)
 try:audit('subprocess.Popen',('/bin/false',['/bin/false'],None,{'SECRET':'not recorded'}))
 except RuntimeError:pass
 ck(more==[dict(event='subprocess.Popen',reason='import_probe_forbidden:subprocess.Popen',path='/bin/false',argv=['/bin/false'])],'denial_omits_process_environment')
(N/('configuration_tests_python'+str(sys.version_info.major)+str(sys.version_info.minor)+'.json')).write_bytes(E(dict(passed=True,count=len(checks),checks=checks,server_contacted=False,native_dependencies_imported=False,captured_source=H(source.read_bytes()))))
print('CONFIGURATION',len(checks))
