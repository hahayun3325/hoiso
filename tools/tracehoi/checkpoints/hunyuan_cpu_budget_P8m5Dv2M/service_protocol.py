"""One model-free service and one identity-checked stop request; no retry/reset/holder API."""
import copy,json,re,time,os,stat
from read_helpers import need,H,E,prefix,typed,run_helper,file_bytes,namespace_snapshot,mount_context,EVENT_CAP,PROC_CAP,canonical,directories,same_directories,close_all,key
from manager_observation import observe as manager_observe,helper_value,SERVICE,MANAGER,status_uids
from cgroup_admission import APP,hierarchy,compare_managers,device
from cgroup_readers import read_group,event_values
A='P8m5Dv2M'
UNIT='tracehoi-hunyuan-worker-'+A+'.service'
GROUP=APP+'/'+UNIT
DESCRIPTION='TraceHOI model-free completion probe '+A
EXEC=['/usr/bin/bash','--noprofile','--norc','-p','-c','/usr/bin/sleep 6 & child=$!; wait "$child"']
BINARIES=['/usr/bin/bash','/usr/bin/sleep']
UNIT_FIELDS={'Description','CollectMode','Id','LoadState','ActiveState','SubState','Transient','InvocationID'}
POLICY=[('Description','s',DESCRIPTION),('Type','s','exec'),('Restart','s','no'),('KillMode','s','control-group'),('SendSIGKILL','b',True),('FinalKillSignal','i',9),('Delegate','b',False),('RemainAfterExit','b',True),('CollectMode','s','inactive'),('RuntimeMaxUSec','t',20000000),('TimeoutStartUSec','t',3000000),('TimeoutStopUSec','t',2000000),('MemoryMax','t',67108864),('TasksMax','t',4),('NoNewPrivileges','b',True),('Slice','s','app.slice'),('StandardOutput','s','null'),('StandardError','s','null'),('WorkingDirectory','s','/'),('UMask','u',63),('Environment','as',['LANG=C','LC_ALL=C']),('UnsetEnvironment','as',['LD_PRELOAD','LD_LIBRARY_PATH','LD_AUDIT','GLIBC_TUNABLES','BASH_ENV','ENV','SHELLOPTS','BASHOPTS','CDPATH','GLOBIGNORE','POSIXLY_CORRECT'])]
LIST_SIG='a(ssssssouso)'

def request(peer):
    props=POLICY+[('ExecStart','a(sasb)',[[EXEC[0],EXEC,False]])]
    argv=prefix()+[peer,MANAGER,SERVICE+'.Manager','StartTransientUnit','ssa(sv)a(sa(sv))',UNIT,'fail',str(len(props))]
    for name,sig,value in props:
        argv.extend([name,sig])
        if sig=='a(sasb)':argv.extend(['1',EXEC[0],str(len(EXEC))]+EXEC+['false'])
        elif sig=='as':argv.extend([str(len(value))]+value)
        else:argv.append(str(value).lower() if type(value)is bool else str(value))
    return argv+['0']

def stop_request(peer):
    return prefix()+[peer,MANAGER,SERVICE+'.Manager','StopUnit','ss',UNIT,'fail']

def list_argv(peer):
    # Unlike ListUnitsByNames in v249, the patterns method does not load a missing unit.
    return prefix()+[peer,MANAGER,SERVICE+'.Manager','ListUnitsByPatterns','asas','0','1',UNIT]

def property_argv(peer,path,name):
    return prefix()+[peer,path,'org.freedesktop.DBus.Properties','Get','ss',SERVICE+('.Unit' if name in UNIT_FIELDS else '.Service'),name]

def list_reply(row,argv):
    need(type(row)is dict and row.get('argv')==argv,'list_helper_command')
    need(all(row.get(k)is True for k in ['launch_started','launch_returned','wait_returned','streams_closed','selector_closed']),'list_helper_completion')
    need(type(row.get('pid'))is int and row['pid']>0 and type(row.get('exit_code'))is int and row['exit_code']==0,'list_helper_exit')
    need(row.get('errors')==[] and all(row.get(k)is False for k in ['timeout','overflow','kill_attempted']),'list_helper_errors')
    need(type(row.get('stdout'))is str and row.get('stderr')=='' and row.get('stderr_binding')==H(b''),'list_helper_streams')
    need(H(row['stdout'].encode())==row.get('stdout_binding') and 0<len(row['stdout'].encode())<=65536,'list_stream_binding')
    def pairs(items):
        out={}
        for k,v in items:need(k not in out,'list_duplicate_key');out[k]=v
        return out
    def reject(_):raise ValueError('list_nonfinite')
    data=json.loads(row['stdout'],object_pairs_hook=pairs,parse_constant=reject)
    need(type(data)is dict and set(data)=={'type','data'} and data['type']==LIST_SIG and type(data['data'])is list and len(data['data'])==1,'list_envelope')
    rows=data['data'][0];need(type(rows)is list and len(rows)<=1,'list_exact_unit_cap')
    for r in rows:
        need(type(r)is list and len(r)==10,'list_row')
        for sig,v in zip(['s']*6+['o','u','s','o'],r):typed(sig,v)
        need(r[0]==UNIT and r[6].startswith('/org/freedesktop/systemd1/unit/'),'list_exact_unit')
    return rows

