"""Read-only cgroup preflight. Absence is a sample, never a unit reservation."""
import copy,os,re
from read_helpers import need,file_bytes,EVENT_CAP,MOUNT
from manager_observation import observe as observe_manager,USER_GROUP
from cgroup_readers import event_values,read_group

ROOT=MOUNT+USER_GROUP
APP=ROOT+'/app.slice'
NAMES=['cgroup.type','cgroup.events','cgroup.controllers','cgroup.subtree_control']

def controllers(raw):
    need(type(raw)is bytes and len(raw)<=EVENT_CAP,'controller_cap')
    if raw in (b'',b'\n'):return []
    need(raw.endswith(b'\n') and b'\n'not in raw[:-1],'controller_line')
    tokens=raw[:-1].decode('ascii').split(' ')
    need(all(re.fullmatch('[a-z][a-z0-9_]*',t) for t in tokens) and len(tokens)==len(set(tokens)),'controller_tokens')
    return sorted(tokens)

def device(route):
    dev=route[-1][1]
    return str(os.major(dev))+':'+str(os.minor(dev))

def hierarchy(context,check,record,reader=file_bytes):
    need(not record and context['mount']==MOUNT and context['root']=='/','hierarchy_context')
    record.update(complete=False,groups=[],errors=[])
    try:
        for path in [ROOT,APP]:
            row=dict(path=path,reads=[]);record['groups'].append(row);values={};group_identity=None
            for name in NAMES:
                check();r={};row['reads'].append(r);raw=reader(path+'/'+name,EVENT_CAP,check,r)
                need(r.get('complete') is True and r.get('errors')==[],'hierarchy_read_complete')
                need(device(r['route'])==context['device'],'cgroup_device')
                need(r['before'][3] in (0,1000) and all(x[4]in (0,1000) for x in r['route']),'cgroup_route_owner')
                observed=r['route'][-1]
                need(observed[0]==path and (group_identity is None or observed==group_identity),'hierarchy_directory_changed')
                group_identity=observed
                row[name+'_text']=raw.decode('ascii')
                if name=='cgroup.type':need(raw==b'domain\n','hierarchy_domain');values[name]='domain'
                elif name=='cgroup.events':
                    values[name]=event_values(raw)
                    need(values[name]['populated']==1 and values[name].get('frozen',0)==0,'live_unfrozen_hierarchy')
                else:values[name]=controllers(raw)
            need(set(values['cgroup.subtree_control'])<=set(values['cgroup.controllers']),'enabled_controllers_available')
            row.update(identity=group_identity,values=values)
        check()
    except BaseException as e:
        record['errors'].append(dict(type=type(e).__name__,message=str(e)[:160]));raise
    record['complete']=True
    return [dict(path=x['path'],identity=x['identity'],values=x['values']) for x in record['groups']]

def compare_managers(a,b):
    need(a['owners']==b['owners'] and a['properties']==b['properties'],'manager_changed_between_observations')
    need([p['identity'] for p in a['processes']]==[p['identity'] for p in b['processes']],'manager_process_changed_between_observations')
    need(a['hosts']==b['hosts'],'host_changed_between_observations')

def observe(plan,check,record,manager=observe_manager,hierarchy_reader=hierarchy,group_reader=read_group):
    need(not record and plan['query_cap']==32 and plan['read_only'] is True,'cgroup_observation_scope')
    need(re.fullmatch('[A-Za-z0-9]{8}',plan['attempt_id']) is not None,'attempt_scope')
    expected=APP+'/tracehoi-hunyuan-worker-'+plan['attempt_id']+'.service'
    need(plan['group']==expected and plan['manager_plan']['query_cap']==16,'fixed_cgroup_target')
    record.update(schema='HunyuanCgroupAdmissionObservation.v1',complete=False,errors=[],managers=[],hierarchy=[],groups=[],queries=[],manager_contacted=False,model_executed=False,service_submitted=False,worker_process_control=False,runtime_authorized=False,p2_satisfied=False,read_only=True,namespace_match_observed=False,cgroup_absence_observed=False,worker_empty_observed=False,unit_name_reserved=False)
    def manager_read():
        row={};record['managers'].append(row)
        try:manager(plan['manager_plan'],check,row)
        finally:
            record['queries']=[q for m in record['managers'] for q in m.get('queries',[])]
            record['manager_contacted']=any(m.get('manager_contacted',False) for m in record['managers'])
        need(row.get('complete') is True and row.get('errors')==[] and row.get('namespace_match_observed') is True,'manager_observation_complete')
        need(len(row.get('queries',[]))==16 and len(record['queries'])<=32,'cgroup_query_count')
        return row
    def kernel_read(context):
        row={};record['hierarchy'].append(row);result=hierarchy_reader(context,check,row)
        need(row.get('complete') is True and row.get('errors')==[],'hierarchy_complete')
        group={};record['groups'].append(group);got=group_reader(dict(group=expected),check,group)
        need(group.get('complete') is True and group.get('errors')==[] and got==dict(path=expected,empty=True,absent=True),'prospective_group_must_be_absent')
        need(device(group['route'])==context['device'],'prospective_parent_device')
        need(group['route'][-1]==row['groups'][-1]['identity'],'prospective_parent_identity')
        return result,copy.deepcopy(group['route'])
    try:
        check();m1=manager_read();context=m1['processes'][0]['identity']['context']
        k1=kernel_read(context);k2=kernel_read(context)
        need(k1==k2,'kernel_hierarchy_changed')
        m2=manager_read();compare_managers(m1,m2)
        need(len(record['queries'])==32,'final_query_count');check()
        record['namespace_match_observed']=True;record['cgroup_absence_observed']=True
    except BaseException as e:
        record['errors'].append(dict(type=type(e).__name__,message=str(e)[:160]));raise
    record['complete']=True
    return record
