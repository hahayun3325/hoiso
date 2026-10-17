"""Build or verify an immutable diagnostic export using explicit candidate IDs."""
import argparse,importlib.util,json,sys
from pathlib import Path

def load(name,root):
 s=importlib.util.spec_from_file_location(name,root/'src/foho/geometry'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
 b=sub.add_parser('build');b.add_argument('manifest');b.add_argument('--sha256',required=True);b.add_argument('--case',required=True);b.add_argument('--review-dir',required=True);b.add_argument('--files-sha256',required=True);b.add_argument('--record');b.add_argument('--candidate',action='append',required=True);b.add_argument('--purpose',required=True);b.add_argument('--output',required=True)
 v=sub.add_parser('verify');v.add_argument('package');v.add_argument('--sha256',required=True);v.add_argument('--case',required=True);v.add_argument('--purpose',required=True)
 a=p.parse_args();root=Path(__file__).resolve().parents[2];names=['scene_candidates','scene_review','hand_domain_review','mask_review_record','scene_readiness','diagnostic_scene_export'];sc,render,viewer,records,ready,export=[load(n,root) for n in names]
 if sys.platform=='linux':
  import resource
  resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(60,60))
 if a.action=='build':
  raw=sc.regular(a.record,128*1024) if a.record else None
  package,files=export.build(a.manifest,a.sha256,a.case,a.review_dir,a.files_sha256,sc,render,viewer,records,ready,candidate_ids=a.candidate,purpose=a.purpose,record_raw=raw)
  export.publish(a.output,files,sc);digest=sc.binding(files['package.json'])['sha256'];out=a.output
 else:out=a.package;digest=a.sha256
 receipt=export.verify(out,digest,a.case,sc,render,viewer,records,ready,purpose=a.purpose)
 print(sc.encode(receipt).decode(),end='')
if __name__=='__main__':main()
