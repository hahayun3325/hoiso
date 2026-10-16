"""Archive two named, never-started CPU attempts, then move their folders to Trash."""
import datetime
import io
import json
import os
from pathlib import Path
import stat
import uuid
from urllib.parse import quote
import zipfile
from file_safety import binding, dirs, exclusive, read, require, route

ALLOWED = {
    'tracehoi-hunyuan-cpu-load-probe-20261014-v1-N7l4Cu9L',
    'tracehoi-hunyuan-cpu-budget-probe-20261014-v1-P8m5Dv2M',
}
EMPTY_DIRS = {'cache','cache/warp','tmp','config','config/matplotlib'}

def snapshot(root, expected):
    route(root);st=root.stat()
    require(stat.S_ISDIR(st.st_mode) and st.st_uid==os.getuid(),'retired_root_owner')
    seen={};count=0
    for base, folders, files in os.walk(root,followlinks=False):
        for name in folders+files:
            p=Path(base)/name;rel=p.relative_to(root).as_posix();s=p.lstat();count+=1
            require(count<=128 and s.st_dev==st.st_dev and s.st_uid==os.getuid(),'retired_entry_bound_or_owner')
            require(not stat.S_ISLNK(s.st_mode),'retired_symlink')
            if stat.S_ISDIR(s.st_mode):
                require(rel in EMPTY_DIRS,'unexpected_retired_directory:'+rel)
            else:
                require(stat.S_ISREG(s.st_mode) and rel in expected,'unexpected_retired_file:'+rel)
                require(binding(read(p,16*1024**2))==expected[rel],'retired_file_changed:'+rel)
            seen[rel]=[s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns]
    return seen

def retain(path, raw):
    if os.path.lexists(path):require(read(path,16*1024**2)==raw,'archive_already_exists_with_different_bytes')
    else:exclusive(path,raw)

def archive_retired(row, home):
    home=Path(home);src=Path(row['folder'])
    require(src.parent==home and src.name in ALLOWED,'retired_folder_scope')
    require(Path(row['terminal']).parent==home,'terminal_scope')
    if not os.path.lexists(src):return dict(row,status='already_absent',archive_created=False)
    raw=read(src/row['zip_name'],16*1024**2)
    require(binding(raw)==row['zip_binding'],'retired_zip_binding')
    terminal=read(row['terminal'],16384)
    require(binding(terminal)==row['terminal_binding'],'retired_terminal_binding')
    with zipfile.ZipFile(io.BytesIO(raw))as z:
        names=z.namelist();require(len(names)<=64 and len(names)==len(set(names)),'retired_archive_names')
        require(all(Path(name).name==name for name in names),'retired_archive_paths')
        require(sum(x.file_size for x in z.infolist())<=16*1024**2,'retired_archive_byte_bound')
        require(z.testzip()is None,'retired_archive_crc')
        report=json.loads(z.read('review_report.json'))
        require(report['attempt_id']==row['attempt_id'],'retired_attempt')
        service=report['service']
        require(service['submission_attempted']is False and service['service_submitted']is False,'attempt_might_have_started')
        expected={name:binding(z.read(name))for name in names}
    expected[row['zip_name']]=row['zip_binding']
    before=snapshot(src,expected)
    archive=home/'tracehoi-evidence-archive'/row['attempt_id'];dirs(archive)
    for p in [archive.parent,archive]:
        require(p.stat().st_uid==os.getuid() and not p.stat().st_mode&0o022,'unsafe_archive_directory')
    retained_zip=archive/row['zip_name'];retained_terminal=archive/Path(row['terminal']).name
    retain(retained_zip,raw);retain(retained_terminal,terminal)
    require(read(retained_zip,16*1024**2)==raw and read(retained_terminal,16384)==terminal,'archive_readback')
    for directory in [archive,archive.parent,home]:
        fd=os.open(str(directory),os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    trash=home/'.local/share/Trash';dirs(trash/'files');dirs(trash/'info')
    for p in [trash,trash/'files',trash/'info']:
        require(p.stat().st_uid==os.getuid() and not p.stat().st_mode&0o022,'unsafe_trash_directory')
    require(src.stat().st_dev==(trash/'files').stat().st_dev,'cross_filesystem_trash')
    name=src.name+'.tracehoi-'+uuid.uuid4().hex;dst=trash/'files'/name
    info=trash/'info'/(name+'.trashinfo')
    exclusive(info,('[Trash Info]\nPath='+quote(str(src),safe='/')+'\nDeletionDate='+datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')+'\n').encode())
    fd=os.open(str(info.parent),os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    require(snapshot(src,expected)==before,'retired_tree_changed_before_move')
    require(not os.path.lexists(dst),'trash_collision')
    os.rename(src,dst)
    result=dict(row,status='trashed',archive_created=True,retained_zip=str(retained_zip),
                retained_terminal=str(retained_terminal),trash=str(dst),trash_info=str(info),restore_to=str(src))
    try:
        # Rename changes the root's metadata, not the recorded children.
        require(snapshot(dst,expected)==before,'retired_tree_changed_after_move')
        for p in [src.parent,archive,trash/'files',trash/'info']:
            fd=os.open(str(p),os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)
    except Exception as error:
        error.cleanup_record=dict(result,status='moved_needs_review',error=type(error).__name__+':'+str(error))
        raise
    return result
