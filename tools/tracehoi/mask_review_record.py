"""Build a bound offline mask review, or validate a returned human record."""
import argparse,importlib.util,json,os,sys
from pathlib import Path

def load(name,root):
    spec=importlib.util.spec_from_file_location(name,root/'src/foho/geometry'/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['build','validate'])
    p.add_argument('manifest');p.add_argument('--sha256',required=True);p.add_argument('--case',required=True)
    p.add_argument('--review-dir',required=True);p.add_argument('--files-sha256',required=True)
    p.add_argument('--output');p.add_argument('--record');p.add_argument('--require-reviewed',action='store_true');a=p.parse_args()
    root=Path(__file__).resolve().parents[2];sc=load('scene_candidates',root);renderer=load('scene_review',root);viewer=load('hand_domain_review',root);mod=load('mask_review_record',root)
    if sys.platform=='linux':
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    report,files=mod.build(a.manifest,a.sha256,a.case,a.review_dir,a.files_sha256,sc,renderer,viewer)
    if a.action=='validate':
        p.error('--record is required for validate') if not a.record else None
        record=mod.parse(sc.regular(a.record,128*1024));result=mod.validate(record,report['context'])
        if a.require_reviewed:sc.require(result['human_review_record_complete'],'human_review_still_pending')
        result['input_file_binding']=sc.binding(sc.regular(a.record,128*1024))
        print(json.dumps(result,sort_keys=True));return
    sc.require(not a.record and not a.require_reviewed and a.output,'build_arguments')
    out=Path(a.output).absolute();sc.require('..' not in out.parts and not os.path.lexists(out),'new_output_required')
    for parent in [*reversed(out.parent.parents),out.parent]:sc.require(parent.is_dir() and not parent.is_symlink(),'output_parent_route')
    out.mkdir(mode=0o700)
    receipt=dict(schema='tracehoi.MaskReviewFiles.v1',manifest_binding=report['context']['manifest_binding'],files={n:sc.binding(b) for n,b in files.items()})
    files['files.json']=sc.encode(receipt)
    for n,b in files.items():
        with (out/n).open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
        sc.require(sc.regular(out/n,8*1024**2)==b,'output_readback')
    fd=os.open(str(out),os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)
    print(json.dumps(dict(complete=True,review_record_complete=False,placement_ready=False,files=len(files)),sort_keys=True))
if __name__=='__main__':main()
