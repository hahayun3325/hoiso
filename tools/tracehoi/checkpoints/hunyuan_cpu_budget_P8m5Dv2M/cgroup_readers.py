"""Exact F8 cgroup reader functions; no kernel writes."""
import copy,os,re,stat
from read_helpers import (need,text,EVENT_CAP,MOUNT,file_bytes,canonical,key,
                          directories,same_directories,close_all)

def event_values(raw):
 out={}
 for line in text(raw,EVENT_CAP).splitlines():
  f=line.split(' ');need(len(f)==2 and re.fullmatch('[a-z_]+',f[0])is not None and f[0]not in out and re.fullmatch('[0-9]{1,20}',f[1])is not None,'cgroup_event_line');v=int(f[1]);need(v<2**64,'cgroup_event_integer');out[f[0]]=v
 need(out.get('populated')in (0,1),'cgroup_populated')
 if 'frozen'in out:need(out['frozen']in (0,1),'cgroup_frozen')
 return out


def read_group(plan,check,record,api=os):
 """Caller-namespace observation; never sufficient alone to authenticate a manager."""
 need(not record,'fresh_group_record');path=plan['group'];p=canonical(path);need(path.startswith(MOUNT+'/user.slice/user-1000.slice/user@1000.service/app.slice/')and re.fullmatch('tracehoi-hunyuan-worker-[A-Za-z0-9]+\\.service',p.name)is not None,'fixed_worker_group');fds=[];record.update(path=path,errors=[],complete=False,reads=[],manager_namespace_authenticated=False)
 try:
  parent=directories(str(p.parent),api,record,fds,check);check()
  try:s=api.stat(p.name,dir_fd=parent,follow_symlinks=False)
  except FileNotFoundError:
   same_directories(api,record,fds,check);check()
   try:api.stat(p.name,dir_fd=parent,follow_symlinks=False)
   except FileNotFoundError:record['observation']=dict(path=path,empty=True,absent=True)
   else:raise ValueError('group_appeared')
  else:
   need(stat.S_ISDIR(s.st_mode),'group_directory');before=key(s);values=[]
   for turn in range(2):
    typ={};ev={}
    record['reads'].extend([typ,ev]);need(file_bytes(path+'/cgroup.type',EVENT_CAP,check,typ,api)==b'domain\n','domain_cgroup');b=file_bytes(path+'/cgroup.events',EVENT_CAP,check,ev,api);values.append(event_values(b));need(values[-1]['populated']==0,'group_populated')
    need(typ['route'][-1][1:]==before and ev['route'][-1][1:]==before,'same_group_directory')
   need(values[0]==values[1]and key(api.stat(p.name,dir_fd=parent,follow_symlinks=False))==before,'group_changed');same_directories(api,record,fds,check);record['observation']=dict(path=path,empty=True,absent=False)
  check()
 except BaseException as e:record['errors'].append(dict(stage='group',type=type(e).__name__,message=str(e)[:160]));raise
 finally:close_all(api,fds,record)
 record['complete']=True;return copy.deepcopy(record['observation'])

