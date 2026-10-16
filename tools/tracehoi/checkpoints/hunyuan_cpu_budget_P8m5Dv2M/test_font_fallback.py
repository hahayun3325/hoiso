from pathlib import Path
import copy,errno,json,os,subprocess,sys,tempfile
import native_worker as nw
from read_helpers import E,H
N=Path(__file__).resolve().parent;checks=[]
def ck(v,n):
 if not v:raise AssertionError(n)
 checks.append(n)
source=N.parent/'model_worker_font_source_return_20261009/packet/source__matplotlib_font_manager.py.txt'
ck(H(source.read_bytes())==dict(bytes=57651,sha256='119f931d556373a707f7a0709645c98e7866b385331e6246b09bba79a6acc576'),'captured_font_manager_pin')
# Calling the hook cannot launch anything. Only the observed help request gets
# PermissionError; alternate executables/arguments/cwd keep the hard failure.
with tempfile.TemporaryDirectory()as temp:
 records=[];audit=nw.audit_for(temp,denials=records)
 exact=('fc-list',['fc-list','--help'],None,{'PRIVATE':'not recorded'})
 for args in [exact,('fc-list',['fc-list','--help'],None,None)]:
  try:audit('subprocess.Popen',args)
  except PermissionError as e:ck(e.errno==errno.EACCES and e.filename=='fc-list','exact_help_permission_denied')
  else:raise AssertionError('launch allowed')
 ck(all(r['action']=='blocked_optional_fontconfig_discovery'and r['errno']==13 and r['error_type']=='PermissionError'and 'PRIVATE'not in str(r)for r in records),'bounded_explicit_denial')
 for args in [
  (),('fc-list',),('fc-list',['fc-list','--help'],None),
  ('/usr/bin/fc-list',['fc-list','--help'],None,None),
  ('fc-list',['fc-list','--format=%{file}\\n'],None,None),
  ('fc-list',['fc-list','--help','extra'],None,None),
  ('fc-list',['fc-list','--help'],'/tmp',None),
  ('fc-list',('fc-list','--help'),None,None),
  ('fc-list',['different','--help'],None,None),
  ('/bin/sh',['/bin/sh','-c','fc-list --help'],None,None)]:
  try:audit('subprocess.Popen',args)
  except RuntimeError:ck(True,'other_launch_hard_denial:'+repr(args))
  else:raise AssertionError('other launch changed')
 for ev in ['socket.bind','socket.connect','socket.connect_ex','os.system','os.posix_spawn','os.fork','os.forkpty','os.exec']:
  try:audit(ev,())
  except RuntimeError:ck(True,'unchanged_denial:'+ev)
  else:raise AssertionError(ev)
 ck(len(records)==16,'denial_cap_retained')
# Execute the captured unmodified discovery functions in a disposable child.
# A fake fc-list would create a marker if the audit hook ever let it start.
for mode in ['old_guard','new_guard']:
 with tempfile.TemporaryDirectory()as temp:
  root=Path(temp).resolve();fonts=root/'fonts';fonts.mkdir();(fonts/'fixture.ttf').write_bytes(b'fixture filename only');(fonts/'ignore.txt').write_bytes(b'not a font')
  tool=root/'fc-list';tool.write_text('#!/bin/sh\nprintf launched > "'+str(root/'unexpected_launch')+'"\nprintf -- "--format\\n"\n');tool.chmod(0o700)
  code="""import ast,json,os,subprocess,sys,types
from pathlib import Path
sys.path.insert(0,MODULES)
import native_worker as nw
tree=ast.parse(Path(SOURCE).read_text())
names={'_get_fontconfig_fonts','findSystemFonts','get_fontext_synonyms','list_fonts'}
nodes=[x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name in names]
assert len(nodes)==4
for x in nodes:x.decorator_list=[]
scope=dict(Path=Path,os=os,subprocess=subprocess,sys=types.SimpleNamespace(platform='linux'),X11FontDirectories=[ROOT+'/fonts'],_log=types.SimpleNamespace(warning=lambda *a:None))
exec(compile(ast.Module(body=nodes,type_ignores=[]),SOURCE,'exec'),scope)
os.environ['PATH']=ROOT
denials=[]
if MODE=='old_guard':
 def hook(event,args):
  if event=='subprocess.Popen':raise RuntimeError('import_probe_forbidden:subprocess.Popen')
else:hook=nw.audit_for(ROOT,denials=denials)
sys.addaudithook(hook)
if MODE=='old_guard':
 try:scope['findSystemFonts']()
 except RuntimeError as e:assert str(e)=='import_probe_forbidden:subprocess.Popen'
 else:raise AssertionError('old failure not reproduced')
else:
 assert scope['_get_fontconfig_fonts']()==[]
 assert scope['findSystemFonts']()==[ROOT+'/fonts/fixture.ttf']
 assert len(denials)==2 and all(x['action']=='blocked_optional_fontconfig_discovery'for x in denials)
assert not Path(ROOT+'/unexpected_launch').exists()
print(json.dumps(dict(passed=True,denials=denials)))
"""
  values=dict(MODULES=str(N),SOURCE=str(source),ROOT=str(root),MODE=mode)
  text=''.join(k+'='+repr(v)+'\n'for k,v in values.items())+code
  child=subprocess.run([sys.executable,'-I','-S','-B','-c',text],capture_output=True,timeout=10)
  ck(child.returncode==0,'captured_discovery:'+mode+':'+child.stderr.decode()[-500:])
  ck(json.loads(child.stdout)['passed'],'discovery_result:'+mode)
  ck(not(root/'unexpected_launch').exists(),'fontconfig_never_started:'+mode)
(N/('font_fallback_tests_python'+str(sys.version_info.major)+str(sys.version_info.minor)+'.json')).write_bytes(E(dict(passed=True,count=len(checks),checks=checks,captured_source=H(source.read_bytes()),server_contacted=False,native_dependencies_imported=False)))
print('FONT_FALLBACK',len(checks))

