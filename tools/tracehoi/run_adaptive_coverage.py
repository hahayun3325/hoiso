"""Build or verify a adaptive surface intervals from exact diagnostic inputs."""
import argparse,importlib.util,sys
from pathlib import Path
NAMES=['scene_candidates','scene_review','hand_domain_review','mask_review_record','scene_readiness','diagnostic_scene_export','mask_validation','candidate_comparison','diagnostic_pipeline','hand_object_distances','surface_coverage','proximity_pipeline']
def load(root,n):
 s=importlib.util.spec_from_file_location(n,root/'src/foho/geometry'/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['build','verify'])
 for n in ['workspace','workspace-sha256','distances','distance-sha256','coverage','coverage-sha256','case','output','purpose']:p.add_argument('--'+n,required=True)
 p.add_argument('--receipt-sha256');a=p.parse_args();root=Path(__file__).resolve().parents[2];mods=[load(root,n) for n in NAMES];m=load(root,'adaptive_coverage');sc=mods[0]
 if sys.platform=='linux':
  import resource
  resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(180,180))
 args=[a.workspace,a.workspace_sha256,a.distances,a.distance_sha256,a.coverage,a.coverage_sha256,a.case,*mods]
 if a.action=='build':
  sc.require(a.receipt_sha256 is None,'build_receipt_not_allowed');report,files=m.build(*args,purpose=a.purpose);mods[5].publish(a.output,files,sc)
  result=dict(receipt_binding=sc.binding(files['files.json']),placement_ready=False,selected_candidate=None)
 else:
  sc.require(a.receipt_sha256 is not None,'receipt_required');result=m.verify(a.output,a.receipt_sha256,*args,purpose=a.purpose)
 print(sc.encode(result).decode(),end='')
if __name__=='__main__':main()
