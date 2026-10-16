"""Compact completion rehearsal record writer; earlier packets are referenced."""
import base64,copy,hashlib,io,json,os,stat,sys,time,zipfile
from pathlib import Path
from read_helpers import E,H,need,canonical,directories,same_directories,close_all,identity

def pinned_hash(path,binding,check,record,api=os):
    p=canonical(path);fds=[];fd=None;record.update(path=path,complete=False,errors=[])
    try:
        parent=directories(str(p.parent),api,record,fds,check);check()
        s=api.stat(p.name,dir_fd=parent,follow_symlinks=False);record['before']=identity(s)
        need(stat.S_ISREG(s.st_mode) and s.st_uid==api.geteuid() and s.st_size==binding['bytes'] and 0<s.st_size<=80*1048576,'pinned_regular_input')
        fd=api.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        record['opened']=identity(api.fstat(fd));need(record['opened']==record['before'],'pinned_open')
        sha=hashlib.sha256();size=0
        while True:
            check();chunk=api.read(fd,min(1048576,binding['bytes']+1-size));size+=len(chunk)
            need(size<=binding['bytes'],'input_grew')
            if not chunk:break
            sha.update(chunk)
        record['binding']=dict(bytes=size,sha256=sha.hexdigest());need(record['binding']==binding,'input_hash')
        record['end']=identity(api.fstat(fd));record['after']=identity(api.stat(p.name,dir_fd=parent,follow_symlinks=False))
        need(record['before']==record['opened']==record['end']==record['after'],'input_changed');same_directories(api,record,fds,check)
    except BaseException as e:
        record['errors'].append(dict(type=type(e).__name__,message=str(e)[:160]));raise
    finally:
        try:
            if fd is not None:api.close(fd);record['file_close_returned']=True
        finally:close_all(api,fds,record)
    record['complete']=True;return record

def interpreter_admission(plan,check,row):
    from interpreter_review import meta,predicates
    path=os.readlink('/proc/self/exe');need(path==plan['path'],'resolved_interpreter')
    s=os.lstat(path);row['admission_metadata']=meta(s);row['admission_predicates']=predicates(s)
    need(all(row['admission_predicates'].values()),'interpreter_policy')
    pinned_hash(path,plan['binding'],check,row)
    need(row['admission_metadata']==plan['metadata']and row['route']==plan['route'],'interpreter_metadata_pin')
    return row

def write_file(root,name,raw):
    need(Path(name).name==name and len(name.encode())<=128 and len(raw)<=(16 if name=='review_report.json'else 8)*1048576,'output_scope')
    path=root/name;fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        view=memoryview(raw)
        while view:
            count=os.write(fd,view);need(count>0,'write_progress');view=view[count:]
        os.fsync(fd)
    finally:os.close(fd)
    need(path.read_bytes()==raw,'output_readback')
    return dict(name=name,**H(raw),fsync_returned=True,close_returned=True)

