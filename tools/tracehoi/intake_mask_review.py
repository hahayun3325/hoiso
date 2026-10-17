"""Validate a portable scene and import a completed review into a new folder."""
import argparse,importlib.util,sys
from pathlib import Path

def load(name,root):
    spec=importlib.util.spec_from_file_location(name,root/'src/foho/geometry'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    for action in ['import','verify']:
        s=sub.add_parser(action);s.add_argument('--package',required=True);s.add_argument('--package-sha256',required=True)
        s.add_argument('--case',required=True);s.add_argument('--output',required=True);s.add_argument('--purpose',required=True)
        if action=='import':s.add_argument('--record')
        else:s.add_argument('--receipt-sha256',required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[2]
    sc,renderer,viewer,records,ready,export,intake=[load(n,root) for n in ['scene_candidates','scene_review','hand_domain_review','mask_review_record','scene_readiness','diagnostic_scene_export','review_intake']]
    if sys.platform=='linux':
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(60,60))
    if a.action=='import':
        raw=sc.regular(a.record,128*1024) if a.record else None
        report,files=intake.build(a.package,a.package_sha256,a.case,sc,renderer,viewer,records,ready,export,record_raw=raw,purpose=a.purpose)
        export.publish(a.output,files,sc);receipt_sha=sc.binding(files['files.json'])['sha256']
    else:receipt_sha=a.receipt_sha256
    receipt=intake.verify(a.output,receipt_sha,a.package,a.package_sha256,a.case,sc,renderer,viewer,records,ready,export,purpose=a.purpose)
    print(sc.encode(receipt).decode(),end='')
if __name__=='__main__':main()
