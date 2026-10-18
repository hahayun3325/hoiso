"""Compare saved candidates without selecting a placement."""
import argparse,importlib.util,sys
from pathlib import Path

def load(name,root):
    spec=importlib.util.spec_from_file_location(name,root/'src/foho/geometry'/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['build','verify'])
    for name in ['package','package-sha256','validation','validation-sha256','case','output','purpose']:p.add_argument('--'+name,required=True)
    p.add_argument('--receipt-sha256');a=p.parse_args();root=Path(__file__).resolve().parents[2]
    sc,render,viewer,records,ready,export,validation,comparison=[load(n,root) for n in ['scene_candidates','scene_review','hand_domain_review','mask_review_record','scene_readiness','diagnostic_scene_export','mask_validation','candidate_comparison']]
    if sys.platform=='linux':
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(90,90))
    args=(a.package,a.package_sha256,a.validation,a.validation_sha256,a.case,sc,render,viewer,records,ready,export,validation)
    if a.action=='build':
        sc.require(a.receipt_sha256 is None,'build_does_not_take_receipt');report,files=comparison.build(*args,purpose=a.purpose);export.publish(a.output,files,sc);digest=sc.binding(files['files.json'])['sha256']
    else:sc.require(a.receipt_sha256 is not None,'receipt_required');digest=a.receipt_sha256
    print(sc.encode(comparison.verify(a.output,digest,*args,purpose=a.purpose)).decode(),end='')
if __name__=='__main__':main()
