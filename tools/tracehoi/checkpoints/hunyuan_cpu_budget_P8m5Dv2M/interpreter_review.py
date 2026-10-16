"""Read-only diagnosis of Q9's exact interpreter predicate; no service code."""
import hashlib, json, os, stat, sys, time
from pathlib import PurePosixPath

ATTEMPT = 'R2p7Fx4N'
BIN = '/home/fredcui/anaconda3/envs/foho/bin'
ALLOWED = tuple(BIN+'/'+n for n in ('python','python3','python3.10'))
PROC = '/proc/self/exe'
CAP = 64*1048576
E = lambda v:(json.dumps(v,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
H = lambda raw:dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def need(ok, message):
    if not ok: raise ValueError(message)

def meta(s):
    return dict(device=s.st_dev,inode=s.st_ino,mode=s.st_mode,
                mode_octal=oct(stat.S_IMODE(s.st_mode)),uid=s.st_uid,gid=s.st_gid,
                size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns,
                links=s.st_nlink)

def route_key(s):
    return (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid)

def predicates(s):
    return dict(regular_file=stat.S_ISREG(s.st_mode),owner_uid_1000=s.st_uid==1000,
                no_group_or_other_write=s.st_mode & 0o022 == 0,
                any_execute_bit=bool(s.st_mode & 0o111),
                positive_size_below_64_MiB=0<s.st_size<CAP)

def error(row,stage,e):
    row.setdefault('errors',[]).append(dict(stage=stage,type=type(e).__name__,message=str(e)[:512]))

def close(fd,row,key,api):
    try:
        api.close(fd);row[key]=True
    except OSError as e:
        row[key]=False;error(row,'close',e)

def open_parents(path,row,fds,check,api=os):
    p=PurePosixPath(path)
    need(p.is_absolute() and str(p)==path and '..' not in p.parts,'canonical_parent')
    row['route']=[]
    fd=api.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fds.append(fd)
    opened=api.fstat(fd)
    row['route'].append(dict(path='/',metadata=meta(opened)))
    need(route_key(opened)==route_key(api.lstat('/')),'root_route_identity')
    prefix=''
    for name in p.parts[1:]:
        check();prefix+='/'+name
        child=api.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);fds.append(child)
        opened=api.fstat(child)
        row['route'].append(dict(path=prefix,metadata=meta(opened)))
        need(route_key(opened)==route_key(api.stat(name,dir_fd=fd,follow_symlinks=False)),'parent_open_identity')
        fd=child
    return fd

def check_parents(row,fds,check,api=os):
    need(len(row['route'])==len(fds),'route_count')
    for i,(r,fd) in enumerate(zip(row['route'],fds)):
        check();opened=api.fstat(fd)
        key=lambda v:tuple(v[k] for k in ('device','inode','mode','uid','gid'))
        need(key(r['metadata'])==route_key(opened),'held_parent_changed')
        named=api.lstat('/') if i==0 else api.stat(PurePosixPath(r['path']).name,dir_fd=fds[i-1],follow_symlinks=False)
        need(key(r['metadata'])==route_key(named),'named_parent_changed')
    row['route_stable']=True

def hash_fd(fd,before,row,check,api=os):
    need(stat.S_ISREG(before.st_mode) and 0<before.st_size<CAP,'hash_regular_size_cap')
    digest=hashlib.sha256();count=0
    while True:
        check();raw=api.read(fd,min(1048576,before.st_size+1-count));count+=len(raw)
        need(count<=before.st_size,'hash_file_grew')
        if not raw: break
        digest.update(raw)
    row['end']=meta(api.fstat(fd))
    need(row['end']==meta(before) and count==before.st_size,'hash_file_changed')
    row['binding']=dict(bytes=count,sha256=digest.hexdigest())

def named_file(path,row,check,api=os):
    row.update(path=path,errors=[],complete=False);fds=[];fd=None
    try:
        parent=open_parents(str(PurePosixPath(path).parent),row,fds,check,api)
        s=api.stat(PurePosixPath(path).name,dir_fd=parent,follow_symlinks=False)
        row['before']=meta(s);row['q9_predicates']=predicates(s)
        row['q9_failed_predicates']=[k for k,v in row['q9_predicates'].items() if not v]
        if stat.S_ISREG(s.st_mode) and 0<s.st_size<CAP:
            fd=api.open(PurePosixPath(path).name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
            row['opened']=meta(api.fstat(fd));need(row['opened']==row['before'],'named_open_identity')
            hash_fd(fd,s,row,check,api)
        else: row['hash_skipped']='not_regular_or_outside_read_cap'
        row['after']=meta(api.stat(PurePosixPath(path).name,dir_fd=parent,follow_symlinks=False))
        need(row['after']==row['before'],'named_file_changed')
        check_parents(row,fds,check,api)
    except Exception as e:error(row,'named_file',e)
    finally:
        if fd is not None:close(fd,row,'file_close_returned',api)
        row['directory_closes']=[]
        for d in reversed(fds):
            c={};close(d,c,'returned',api);row['directory_closes'].append(c)
            row['errors'].extend(c.get('errors',[]))
    row['complete']=not row['errors']
    return row

def running_file(row,check,api=os):
    row.update(path=PROC,errors=[],complete=False);fd=None
    try:
        # /proc/self/exe is intentionally followed: it is the current process image.
        row['target_before']=api.readlink(PROC)
        fd=api.open(PROC,os.O_RDONLY|os.O_NONBLOCK)
        s=api.fstat(fd);row['opened']=meta(s);row['q9_predicates']=predicates(s)
        if stat.S_ISREG(s.st_mode) and 0<s.st_size<CAP:hash_fd(fd,s,row,check,api)
        else:row['hash_skipped']='not_regular_or_outside_read_cap'
        row['after']=meta(api.fstat(fd));need(row['after']==row['opened'],'running_image_changed')
        row['target_after']=api.readlink(PROC)
        need(row['target_before']==row['target_after'],'running_target_changed')
    except Exception as e:error(row,'running_file',e)
    finally:
        if fd is not None:close(fd,row,'file_close_returned',api)
    row['complete']=not row['errors']
    return row

def alias_metadata(path,check,api=os):
    row=dict(path=path,errors=[],complete=False);fds=[]
    try:
        parent=open_parents(str(PurePosixPath(path).parent),row,fds,check,api)
        name=PurePosixPath(path).name;check()
        try:s=api.stat(name,dir_fd=parent,follow_symlinks=False)
        except FileNotFoundError:
            row['exists']=False
            try:api.stat(name,dir_fd=parent,follow_symlinks=False)
            except FileNotFoundError:pass
            else:raise ValueError('alias_appeared')
        else:
            row['exists']=True;row['before']=meta(s);row['q9_predicates']=predicates(s)
            if stat.S_ISLNK(s.st_mode):row['link_target']=api.readlink(name,dir_fd=parent)
            check();row['after']=meta(api.stat(name,dir_fd=parent,follow_symlinks=False))
            need(row['after']==row['before'],'alias_changed')
            if 'link_target' in row:need(api.readlink(name,dir_fd=parent)==row['link_target'],'alias_target_changed')
        check_parents(row,fds,check,api)
    except Exception as e:error(row,'alias_metadata',e)
    finally:
        row['directory_closes']=[]
        for d in reversed(fds):
            c={};close(d,c,'returned',api);row['directory_closes'].append(c)
            row['errors'].extend(c.get('errors',[]))
    row['complete']=not row['errors'];return row

def observe(check,api=os):
    row=dict(schema='HunyuanInterpreterObservation.v1',complete=False,errors=[],
             read_only=True,manager_contacted=False,model_executed=False,
             service_submitted=False,permissions_changed=False,
             runtime_authorized=False,admission_approved=False,aliases=[],named={},running={})
    try:
        check();row['resolved_path']=api.readlink(PROC)
        row['resolved_path_allowed']=row['resolved_path'] in ALLOWED
        for path in ALLOWED:row['aliases'].append(alias_metadata(path,check,api))
        # No arbitrary path supplied by the proc link is opened.
        if row['resolved_path_allowed']:named_file(row['resolved_path'],row['named'],check,api)
        else:error(row,'scope',ValueError('resolved_interpreter'))
        running_file(row['running'],check,api)
        check();row['resolved_path_after']=api.readlink(PROC)
        need(row['resolved_path_after']==row['resolved_path'],'resolved_path_changed')
        n=row['named'];r=row['running']
        row['q9_failed_predicates']=n.get('q9_failed_predicates')
        row['q9_policy_passed']=bool(n and n.get('q9_predicates') and all(n['q9_predicates'].values()))
        row['same_running_and_named_identity']=bool(n.get('before') and n['before']==r.get('opened'))
        row['same_running_and_named_bytes']=bool(n.get('binding') and n['binding']==r.get('binding'))
        row['diagnosis_scope']='current observation; does not prove historical Q9 metadata'
        row['complete']=bool(row['resolved_path_allowed'] and not row['errors'] and n.get('complete') and r.get('complete') and all(x['complete'] for x in row['aliases']) and row['same_running_and_named_identity'])
        if not row['same_running_and_named_identity']:error(row,'comparison',ValueError('running_named_identity_mismatch'))
        if n.get('binding') and r.get('binding') and not row['same_running_and_named_bytes']:
            error(row,'comparison',ValueError('running_named_bytes_mismatch'));row['complete']=False
    except Exception as e:error(row,'observation',e)
    if row['errors']:row['complete']=False
    return row
