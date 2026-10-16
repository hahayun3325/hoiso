"""One bounded, read-only manager observation. No service mutation or model API."""
import copy,os,re,stat
from read_helpers import (E,H,need,prefix,reply,run_helper,file_bytes,namespace_snapshot,
                         mount_context,observe_host,PROC_CAP,EVENT_CAP)
BUS='org.freedesktop.DBus';BUS_PATH='/org/freedesktop/DBus'
SERVICE='org.freedesktop.systemd1';MANAGER='/org/freedesktop/systemd1'
USER_GROUP='/user.slice/user-1000.slice/user@1000.service'

def stat_identity(raw,pid):
    text=raw.decode('ascii');left=text.find(' (');right=text.rfind(') ')
    need(left>0 and right>left and text[:left]==str(pid),'process_stat_pid')
    fields=text[right+2:].split()
    need(text[left+2:right]=='systemd' and len(fields)>=20 and fields[0] not in ['Z','X','x'],'live_systemd_process')
    need(fields[19].isdigit() and 0<int(fields[19])<2**64,'process_start_ticks')
    return dict(pid=pid,comm='systemd',start_ticks=int(fields[19]))

def status_uids(raw):
    text=raw.decode('ascii');rows=[s for s in text.splitlines() if s.startswith('Uid:')]
    need(len(rows)==1 and rows[0].split()==['Uid:','1000','1000','1000','1000'],'manager_uid_fields')
    return [1000]*4

def process_snapshot(pid,check,record,api=os):
    need(type(pid)is int and 1<pid<2**31 and not record,'manager_process_scope')
    record.update(pid=pid,complete=False,reads=[],namespace={},errors=[])
    def read(name,cap):
        row={};record['reads'].append(row)
        return file_bytes('/proc/'+str(pid)+'/'+name,cap,check,row,api,1000)
    try:
        start=read('stat',EVENT_CAP);who=stat_identity(start,pid)
        status=read('status',PROC_CAP);uids=status_uids(status)
        m=read('mountinfo',PROC_CAP);c=read('cgroup',EVENT_CAP)
        namespace_snapshot(pid,check,record['namespace'],api)
        end=read('stat',EVENT_CAP);need(stat_identity(end,pid)==who,'manager_pid_reused')
        context=mount_context(m,c)
        need(context['membership']==USER_GROUP+'/init.scope','manager_membership')
        record.update(stat_before_text=start.decode('ascii'),stat_after_text=end.decode('ascii'),
                      status_text=status.decode('ascii'),mountinfo_text=m.decode('ascii'),cgroup_text=c.decode('ascii'))
        record['identity']=dict(**who,uids=uids,context=context,
            namespace={k:v['target'] for k,v in record['namespace']['values'].items()})
        check()
    except BaseException as e:
        record['errors'].append(dict(type=type(e).__name__,message=str(e)[:160]));raise
    record['complete']=True;return copy.deepcopy(record['identity'])

def helper_value(row,argv,sig,variant):
    need(type(row)is dict and row.get('argv')==argv,'helper_command')
    need(all(row.get(k)is True for k in ['launch_started','launch_returned','wait_returned','streams_closed','selector_closed']),'helper_completion')
    need(type(row.get('pid'))is int and row['pid']>0 and type(row.get('exit_code'))is int and row['exit_code']==0,'helper_exit')
    need(row.get('errors')==[] and all(row.get(k)is False for k in ['timeout','overflow','kill_attempted']),'helper_errors')
    need(type(row.get('stdout'))is str and row.get('stderr')=='' and row.get('stdout_binding')==H(row['stdout'].encode()) and row.get('stderr_binding')==H(b''),'helper_streams')
    return reply(row['stdout'].encode(),sig,variant)

def argv_for(label,peer=None):
    base=prefix()
    if label=='bus_id':return base+[BUS,BUS_PATH,BUS,'GetId','']
    if label=='owner':return base+[BUS,BUS_PATH,BUS,'GetNameOwner','s',SERVICE]
    need(type(peer)is str and re.fullmatch(r':[0-9]+\.[0-9]+',peer) is not None and len(peer)<=64,'unique_destination')
    if label in ['uid','pid']:
        return base+[BUS,BUS_PATH,BUS,'GetConnectionUnixUser' if label=='uid' else 'GetConnectionUnixProcessID','s',peer]
    need(label in ['Version','Features'],'finite_read_only_property')
    return base+[peer,MANAGER,'org.freedesktop.DBus.Properties','Get','ss',SERVICE+'.Manager',label]

def compare_context(host,manager):
    sample=host['samples'][0]
    need(manager['namespace']=={k:v['target'] for k,v in sample['namespace']['values'].items()},'manager_namespace_mismatch')
    need(all(manager['context'][k]==sample['context'][k] for k in ['mount_id','device','root','mount']),'manager_mount_mismatch')
    need(sample['context']['membership'].startswith(USER_GROUP+'/'),'caller_user_manager_membership')

def observe(plan,check,record,runner=run_helper,host_reader=observe_host,process_reader=process_snapshot):
    need(not record and plan['uid']==1000 and plan['query_cap']==16,'observation_scope')
    record.update(schema='HunyuanManagerObservation.v1',complete=False,errors=[],queries=[],owners=[],
                  hosts=[],processes=[],properties=[],read_only=True,manager_contacted=False,
                  model_executed=False,service_submitted=False,worker_process_control=False,
                  runtime_authorized=False,p2_satisfied=False,namespace_match_observed=False)
    def call(label,peer=None,sig='s',variant=False):
        check();need(len(record['queries'])<16,'query_cap');argv=argv_for(label,peer)
        row=dict(label=label,argv=argv,result=None);record['queries'].append(row);record['manager_contacted']=True
        try:got=runner(argv,check)
        except BaseException as e:row['result']=copy.deepcopy(getattr(e,'helper_record',None));raise
        row['result']=copy.deepcopy(got);check();return helper_value(got,argv,sig,variant)
    def owner():
        bid=call('bus_id');peer=call('owner')
        need(re.fullmatch('[0-9a-f]{32}',bid) is not None,'bus_guid')
        uid=call('uid',peer,'u');pid=call('pid',peer,'u')
        need(uid==1000 and 1<pid<2**31,'manager_credentials')
        need(call('owner')==peer and call('bus_id')==bid,'manager_owner_race')
        got=dict(bus_id=bid,unique_name=peer,uid=uid,pid=pid);record['owners'].append(got);return got
    def host():
        row={};record['hosts'].append(row);host_reader(plan['host_plan'],check,row)
        need(row.get('complete') is True and row.get('errors')==[],'host_complete')
        need(all(s['tool']['binding']==plan['tool_binding'] for s in row['samples']),'pinned_busctl_changed')
        return row
    def process(pid):
        row={};record['processes'].append(row);got=process_reader(pid,check,row)
        need(row.get('complete') is True and row.get('errors')==[],'process_complete');return got
    def properties(peer):
        got={k:call(k,peer,'s',True) for k in ['Version','Features']}
        need(bool(got['Version']) and len(got['Version'])<=1024,'manager_version')
        record['properties'].append(got);return got
    try:
        h1=host();o1=owner();p1=process(o1['pid']);compare_context(h1,p1);v1=properties(o1['unique_name'])
        v2=properties(o1['unique_name']);p2=process(o1['pid']);o2=owner();h2=host()
        need(o1==o2 and p1==p2 and v1==v2,'manager_changed')
        need(h1==h2,'host_changed_across_queries');compare_context(h2,p2)
        need(len(record['queries'])==16,'query_count');check();record['namespace_match_observed']=True
    except BaseException as e:
        record['errors'].append(dict(type=type(e).__name__,message=str(e)[:160]));raise
    record['complete']=True;return record
