"""Prepare or verify a separate reference-mask evaluation without changing inputs."""
import argparse,importlib.util,sys
from pathlib import Path

def load(name,root):
    spec=importlib.util.spec_from_file_location(name,root/'src/foho/geometry'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['build','verify']);p.add_argument('--package',required=True)
    p.add_argument('--package-sha256',required=True);p.add_argument('--case',required=True);p.add_argument('--output',required=True);p.add_argument('--purpose',required=True)
    p.add_argument('--reference');p.add_argument('--receipt-sha256');a=p.parse_args();root=Path(__file__).resolve().parents[2]
    sc,render,viewer,records,ready,export,validation=[load(n,root) for n in ['scene_candidates','scene_review','hand_domain_review','mask_review_record','scene_readiness','diagnostic_scene_export','mask_validation']]
    if sys.platform=='linux':
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    args=(a.package,a.package_sha256,a.case,sc,render,viewer,records,ready,export)
    if a.action=='build':
        sc.require(a.receipt_sha256 is None,'build_does_not_take_receipt')
        raw=sc.regular(a.reference,1024**2) if a.reference else None
        report,files=validation.build(*args,reference_raw=raw,purpose=a.purpose);export.publish(a.output,files,sc);digest=sc.binding(files['files.json'])['sha256']
    else:
        sc.require(a.reference is None and a.receipt_sha256 is not None,'verify_uses_embedded_reference_and_receipt');digest=a.receipt_sha256
    result=validation.verify(a.output,digest,*args,purpose=a.purpose);print(sc.encode(result).decode(),end='')
if __name__=='__main__':main()
