"""Build an offline interactive review of the authenticated hand-domain audit."""
import argparse,importlib.util,json,os,sys
from pathlib import Path

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest');parser.add_argument('--sha256',required=True);parser.add_argument('--case',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--audit-dir',required=True);parser.add_argument('--audit-sha256',required=True);parser.add_argument('--files-sha256',required=True)
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    reader=load('scene_candidates',root/'src/foho/geometry/scene_candidates.py')
    renderer=load('scene_review',root/'src/foho/geometry/scene_review.py')
    review=load('hand_domain_review',root/'src/foho/geometry/hand_domain_review.py')
    output=Path(args.output).absolute();reader.require('..' not in output.parts and not os.path.lexists(output),'new_output_required')
    for p in [*reversed(output.parent.parents),output.parent]:reader.require(p.is_dir() and not p.is_symlink(),'output_parent_route')
    if sys.platform=='linux':
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    report,files=review.build_review(args.manifest,args.sha256,args.case,args.audit_dir,args.audit_sha256,args.files_sha256,reader,renderer)
    output.mkdir(mode=0o700)
    for n,b in files.items():
        with (output/n).open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
        reader.require(reader.regular(output/n,8*1024**2)==b,'output_readback')
    receipt=dict(schema='tracehoi.HandDomainReviewFiles.v1',manifest_binding=report['manifest_binding'],files={n:reader.binding(b) for n,b in files.items()})
    with (output/'files.json').open('xb') as f:f.write(reader.encode(receipt));f.flush();os.fsync(f.fileno())
    fd=os.open(str(output),os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    print(json.dumps(dict(complete=True,output=str(output),candidates=len(report['audit']['candidates']),placement_ready=False,files=len(files)),sort_keys=True))

if __name__=='__main__':main()
