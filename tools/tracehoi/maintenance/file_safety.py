"""Bounded regular-file reads and exclusive writes for maintenance."""
import hashlib,json,os,stat
from pathlib import Path
from urllib.parse import quote

def encoded(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def binding(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def require(ok,message):
    if not ok:raise ValueError(message)
def route(path):
    p=Path(path)
    require(p.is_absolute() and '..' not in p.parts,'absolute_route_required')
    for q in [*reversed(p.parents),p]:
        s=q.lstat();require(not stat.S_ISLNK(s.st_mode),'symlink_route:'+str(q))
    return p

def read(path,cap=8*1024**2):
    p=route(path);a=p.stat();require(stat.S_ISREG(a.st_mode) and a.st_size<=cap,'file_bound:'+str(p))
    fd=os.open(str(p),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    key=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    try:
        require(key(a)==key(os.fstat(fd)),'opened_file_changed')
        with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(cap+1)
        require(len(raw)<=cap and key(a)==key(os.fstat(fd))==key(p.stat()),'read_changed')
        return raw
    finally:os.close(fd)

def exclusive(path,raw):
    p=Path(path);route(p.parent)
    with p.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    require(read(p,max(len(raw),1))==raw,'write_readback')

def dirs(path):
    p=Path(path)
    for q in [*reversed(p.parents),p]:
        if not q.exists():q.mkdir(mode=0o700)
        require(stat.S_ISDIR(q.lstat().st_mode),'directory_route')

