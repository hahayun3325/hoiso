"""Exact selected stdlib helpers from verified F8; see helper_lineage.json."""

import copy,hashlib,json,os,re,selectors,stat,subprocess,time

from pathlib import PurePosixPath

E=lambda x:(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


H=lambda b:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())


def need(v,n):
    if not v: raise ValueError(n)


def key(s):return [s.st_dev,s.st_ino,s.st_mode,s.st_uid]


def identity(s):return key(s)+[s.st_size,s.st_mtime_ns,s.st_ctime_ns]


def canonical(path):
 need(type(path)is str and 1<len(path)<=1024 and '\x00'not in path,'path_text');p=PurePosixPath(path);need(p.is_absolute()and str(p)==path and '..'not in p.parts,'canonical_path');return p


def directories(path,a,record,fds,check):
 p=canonical(path);fd=a.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fds.append(fd);rows=[['/',*key(a.fstat(fd))]]
 need(key(a.lstat('/'))==rows[0][1:]and stat.S_ISDIR(rows[0][3]),'root_directory')
 prefix=''
 for part in p.parts[1:]:
  check();prefix+='/'+part;child=a.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);fds.append(child);s=a.fstat(child);need(stat.S_ISDIR(s.st_mode),'directory_type');need(key(a.stat(part,dir_fd=fd,follow_symlinks=False))==key(s),'directory_open_identity');rows.append([prefix,*key(s)]);fd=child
 record['route']=rows;return fd


def same_directories(a,record,fds,check):
 rows=record['route'];need(key(a.lstat('/'))==rows[0][1:],'root_route_changed')
 for i,row in enumerate(rows):
  check();need(key(a.fstat(fds[i]))==row[1:],'held_directory_changed')
  if i:need(key(a.stat(PurePosixPath(row[0]).name,dir_fd=fds[i-1],follow_symlinks=False))==row[1:],'directory_route_changed')


def close_all(a,fds,record):
 record['descriptor_closes']=[]
 for fd in reversed(fds):
  try:a.close(fd);record['descriptor_closes'].append(True)
  except BaseException as e:record['descriptor_closes'].append(False);record['errors'].append(dict(stage='close',type=type(e).__name__,message=str(e)[:160]))
 need(all(record['descriptor_closes']),'descriptor_close_failed')


TOOL='/usr/bin/busctl'


MOUNT='/sys/fs/cgroup'


TOOL_CAP=2*1048576


PROC_CAP=256*1024


EVENT_CAP=4096


def file_bytes(path,cap,check,record,api=os,owner=None,executable=False):
 need(type(record)is dict and not record,'fresh_read_record');p=canonical(path);need(type(cap)is int and 0<cap<=TOOL_CAP,'read_cap');fds=[];fd=None;raw=bytearray();record.update(path=path,errors=[],complete=False)
 try:
  parent=directories(str(p.parent),api,record,fds,check);check();s=api.stat(p.name,dir_fd=parent,follow_symlinks=False);record['before']=identity(s)
  need(stat.S_ISREG(s.st_mode)and 0<=s.st_size<=cap,'regular_capped_file')
  if owner is not None:need(s.st_uid==owner,'file_owner')
  if executable:
   need(s.st_uid==0 and s.st_mode&0o022==0 and s.st_mode&0o111,'root_owned_executable')
   need(all(row[4]==0 and row[3]&0o022==0 for row in record['route']),'root_owned_tool_route')
  fd=api.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent);record['opened']=identity(api.fstat(fd));need(record['opened']==record['before'],'opened_file_identity')
  while True:
   check();part=api.read(fd,min(65536,cap+1-len(raw)));need(type(part)is bytes,'read_bytes');raw.extend(part);need(len(raw)<=cap,'read_byte_cap')
   if not part:break
  if executable:need(bytes(raw).startswith(b'\x7fELF')and len(raw)==s.st_size,'elf_tool_bytes')
  record['end']=identity(api.fstat(fd));record['after']=identity(api.stat(p.name,dir_fd=parent,follow_symlinks=False));need(record['before']==record['opened']==record['end']==record['after'],'file_changed');same_directories(api,record,fds,check);record['binding']=H(bytes(raw))
 except BaseException as e:record['errors'].append(dict(stage='read',type=type(e).__name__,message=str(e)[:160]));raise
 finally:
  try:
   if fd is not None:api.close(fd);record['file_close_returned']=True
  finally:close_all(api,fds,record)
 record['complete']=True;return bytes(raw)


def socket_snapshot(uid,check,record,api=os):
 need(type(uid)is int and uid==1000 and not record,'socket_scope');path='/run/user/1000/bus';fds=[];record.update(path=path,errors=[],complete=False)
 try:
  parent=directories('/run/user/1000',api,record,fds,check)
  need(all(row[4]==0 and row[3]&0o022==0 for row in record['route'][:-1]),'socket_system_route')
  leaf=record['route'][-1];need(leaf[4]==uid and stat.S_IMODE(leaf[3])==0o700,'private_user_runtime')
  check();s=api.stat('bus',dir_fd=parent,follow_symlinks=False);record['before']=identity(s);need(stat.S_ISSOCK(s.st_mode)and s.st_uid==uid,'user_bus_socket')
  same_directories(api,record,fds,check);check();record['after']=identity(api.stat('bus',dir_fd=parent,follow_symlinks=False));need(record['before']==record['after'],'socket_changed')
 except BaseException as e:record['errors'].append(dict(stage='socket',type=type(e).__name__,message=str(e)[:160]));raise
 finally:close_all(api,fds,record)
 record['complete']=True;return record


def text(raw,cap):
 need(type(raw)is bytes and 0<len(raw)<=cap,'kernel_text_cap');out=raw.decode('ascii');need('\x00'not in out and out.endswith('\n'),'kernel_text');return out


def mount_context(mountinfo,cgroup):
 # Accept one full cgroup2 mount at the fixed path, with no submount hiding it.
 # No escaped/relative path is interpreted as a host path.
 rows=[]
 for line in text(mountinfo,PROC_CAP).splitlines():
  fields=line.split(' ');need(fields.count('-')==1,'mount_separator');i=fields.index('-');need(i>=6 and len(fields)==i+4,'mount_fields')
  need(fields[0].isdigit()and fields[1].isdigit()and re.fullmatch('[0-9]+:[0-9]+',fields[2])is not None,'mount_numbers')
  point=fields[4]
  if fields[i+1]=='cgroup2' or point==MOUNT or point.startswith(MOUNT+'/'):rows.append(fields)
 need(len(rows)==1,'one_unshadowed_cgroup2_mount');r=rows[0];i=r.index('-');need(r[3]=='/'and r[4]==MOUNT and r[i+1]=='cgroup2','full_cgroup2_mount')
 paths=[]
 for line in text(cgroup,EVENT_CAP).splitlines():
  f=line.split(':',2);need(len(f)==3 and f[0].isdigit(),'membership_fields')
  if f[0]=='0':need(f[1]=='','unified_membership');paths.append(f[2])
 need(len(paths)==1,'one_unified_membership');path=paths[0]
 if path!='/':canonical(path)
 need(not path.endswith(' (deleted)')and '\\'not in path,'live_membership_path')
 return dict(mount_id=int(r[0]),device=r[2],root='/',mount=MOUNT,membership=path,manager_namespace_authenticated=False)


def namespace_snapshot(pid,check,record,api=os):
 need(type(pid)is int and 0<pid<2**31 and not record,'namespace_pid');fds=[];record.update(pid=pid,errors=[],complete=False)
 try:
  fd=directories('/proc/'+str(pid)+'/ns',api,record,fds,check);values={}
  for name in ['mnt','cgroup']:
   check();s=api.stat(name,dir_fd=fd,follow_symlinks=False);need(stat.S_ISLNK(s.st_mode),'namespace_link');before=identity(s);value=api.readlink(name,dir_fd=fd);need(type(value)is str and re.fullmatch(name+r':\[[0-9]+\]',value)is not None,'namespace_link_value');check();need(identity(api.stat(name,dir_fd=fd,follow_symlinks=False))==before and api.readlink(name,dir_fd=fd)==value,'namespace_changed');values[name]=dict(identity=before,target=value)
  same_directories(api,record,fds,check);record['values']=values
 except BaseException as e:record['errors'].append(dict(stage='namespace',type=type(e).__name__,message=str(e)[:160]));raise
 finally:close_all(api,fds,record)
 record['complete']=True;return record


def observe_host(plan,check,record,api=os):
 """One paired census of the current process. No query or helper process."""
 need(not record and plan['uid']==api.geteuid()==1000,'host_scope');pid=api.getpid();record.update(schema='HunyuanHostObservation.v1',plan_binding=H(E(plan)),pid=pid,samples=[],errors=[],complete=False,read_only=True,manager_contacted=False,model_executed=False,runtime_authorized=False)
 try:
  for label in ['before','after']:
   row=dict(label=label,tool={},socket={},mountinfo={},cgroup={},namespace={});record['samples'].append(row)
   file_bytes(TOOL,TOOL_CAP,check,row['tool'],api,0,True);socket_snapshot(1000,check,row['socket'],api)
   m=file_bytes('/proc/'+str(pid)+'/mountinfo',PROC_CAP,check,row['mountinfo'],api,1000);c=file_bytes('/proc/'+str(pid)+'/cgroup',EVENT_CAP,check,row['cgroup'],api,1000);namespace_snapshot(pid,check,row['namespace'],api)
   row['mountinfo_text']=m.decode('ascii');row['cgroup_text']=c.decode('ascii');row['context']=mount_context(m,c)
  need({k:v for k,v in record['samples'][0].items()if k!='label'}=={k:v for k,v in record['samples'][1].items()if k!='label'},'host_snapshot_changed');check()
 except BaseException as e:record['errors'].append(dict(stage='host',type=type(e).__name__,message=str(e)[:160]));raise
 record['complete']=True;return record


OUTPUT_CAP=65536;TIMEOUT=3.0;QUERY_CAP=192


OUTPUT_CAP=65536;TIMEOUT=3.0;QUERY_CAP=192


def typed(sig,value):
 if sig in ['s','o']:
  need(type(value)is str and len(value.encode('utf-8'))<=16384 and all(ord(c)>=32 and ord(c)!=127 for c in value),'wire_string')
  if sig=='o':need(re.fullmatch(r'/(?:[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*)?',value)is not None,'wire_object_path')
 elif sig=='b':need(type(value)is bool,'wire_boolean')
 elif sig in ['y','u','i','t']:
  lo,hi={'y':(0,256),'u':(0,2**32),'i':(-2**31,2**31),'t':(0,2**64)}[sig];need(type(value)is int and lo<=value<hi,'wire_integer:'+sig)
 elif sig in ['as','ay']:
  need(type(value)is list and len(value)<=256,'wire_array')
  for x in value:typed('s'if sig=='as'else'y',x)
 elif sig=='a(sasbttttuii)':
  need(type(value)is list and len(value)==1 and type(value[0])is list and len(value[0])==10,'wire_exec_shape')
  for s,v in zip(['s','as','b','t','t','t','t','u','i','i'],value[0]):typed(s,v)
 else:raise ValueError('wire_unsupported_signature')
 return value


def reply(raw,sig,variant=False):
 need(type(raw)is bytes and 0<len(raw)<=OUTPUT_CAP,'wire_reply_cap')
 def pairs(rows):
  out={}
  for k,v in rows:need(k not in out,'wire_duplicate_key');out[k]=v
  return out
 def nonfinite(_):raise ValueError('wire_nonfinite')
 try:value=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=nonfinite)
 except (UnicodeError,RecursionError)as e:raise ValueError('wire_json_encoding_or_depth')from e
 need(type(value)is dict and set(value)=={'type','data'}and value['type']==('v'if variant else sig)and type(value['data'])is list and len(value['data'])==1,'wire_message_envelope')
 result=value['data'][0]
 if variant:
  need(type(result)is dict and set(result)=={'type','data'}and result['type']==sig,'wire_variant_signature');result=result['data']
 return copy.deepcopy(typed(sig,result))


def run_helper(argv,check,os_api=os,process_api=subprocess,selector_factory=selectors.DefaultSelector,clock=time.monotonic):
 """One direct helper with bounded streams and wait. No shell or descendant guarantee.
 Session constructs the exact read-only argv; this low-level seam is not launch authority.
 Popen/OS operations themselves cannot be interrupted by a cooperative deadline.
 """
 need(type(argv)is list and 1<=len(argv)<=512 and all(type(x)is str and '\0'not in x for x in argv)and sum(len(x.encode())for x in argv)<=32768,'helper_argv')
 row=dict(argv=list(argv),launch_started=False,launch_returned=False,pid=None,exit_code=None,stdout=None,stderr=None,timeout=False,overflow=False,kill_attempted=False,wait_returned=False,streams_closed=False,selector_closed=False,errors=[])
 p=None;sel=None;buffers={'stdout':bytearray(),'stderr':bytearray()};fatal=None;started=clock()
 def failure(stage,e):
  nonlocal fatal
  row['errors'].append(dict(stage=stage,type=type(e).__name__,message=str(e)[:160]))
  if not isinstance(e,Exception)and fatal is None:fatal=e
 try:
  check();row['launch_started']=True
  p=process_api.Popen(list(argv),stdin=process_api.DEVNULL,stdout=process_api.PIPE,stderr=process_api.PIPE,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'},close_fds=True,shell=False)
  row['launch_returned']=True;row['pid']=p.pid;sel=selector_factory()
  for name in buffers:
   stream=getattr(p,name);os_api.set_blocking(stream.fileno(),False);sel.register(stream,selectors.EVENT_READ,name)
  while sel.get_map():
   check();remaining=TIMEOUT-(clock()-started)
   if remaining<=0:row['timeout']=True;raise ValueError('helper_timeout')
   for key,_ in sel.select(min(remaining,.1)):
    raw=os_api.read(key.fileobj.fileno(),min(4096,OUTPUT_CAP+1-sum(map(len,buffers.values()))));need(type(raw)is bytes,'helper_read_bytes')
    if not raw:sel.unregister(key.fileobj)
    else:buffers[key.data].extend(raw)
    if sum(map(len,buffers.values()))>OUTPUT_CAP:row['overflow']=True;raise ValueError('helper_output_cap')
  check();remaining=TIMEOUT-(clock()-started)
  if remaining<=0:row['timeout']=True;raise ValueError('helper_timeout')
  row['exit_code']=p.wait(timeout=remaining);row['wait_returned']=True
 except BaseException as e:failure('run',e)
 finally:
  if p is not None and not row['wait_returned']:
   try:
    if p.poll()is None:row['kill_attempted']=True;p.kill()
   except BaseException as e:failure('kill',e)
   try:row['exit_code']=p.wait(timeout=1.0);row['wait_returned']=True
   except BaseException as e:failure('wait',e)
  if sel is not None:
   try:sel.close();row['selector_closed']=True
   except BaseException as e:failure('selector_close',e)
  if p is not None:
   closed=[]
   for name in buffers:
    try:getattr(p,name).close();closed.append(True)
    except BaseException as e:closed.append(False);failure(name+'_close',e)
   row['streams_closed']=all(closed)
  for name,raw in buffers.items():
   row[name+'_binding']=H(bytes(raw))
   try:row[name]=bytes(raw).decode('utf-8')
   except UnicodeError as e:failure(name+'_decode',e)
 if fatal is not None:fatal.helper_record=copy.deepcopy(row);raise fatal
 return row


def prefix():
 return ['/usr/bin/busctl','--address=unix:path=/run/user/1000/bus','--no-pager','--auto-start=no','--allow-interactive-authorization=no','--timeout=2s','--json=short','--','call']

