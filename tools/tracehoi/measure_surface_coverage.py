"""Measure area-weighted proximity intervals for saved diagnostic hand surfaces."""
import argparse,importlib.util,sys
from pathlib import Path
def load(name,root):
    spec=importlib.util.spec_from_file_location(name,root/'src/foho/geometry'/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['build','verify'])
    for n in ['workspace','workspace-sha256','distances','distance-sha256','case','output','purpose']:p.add_argument('--'+n,required=True)
    p.add_argument('--receipt-sha256');a=p.parse_args();root=Path(__file__).resolve().parents[2]
    modules=[load(n,root) for n in ['scene_candidates','scene_review','hand_domain_review','mask_review_record','scene_readiness','diagnostic_scene_export','mask_validation','candidate_comparison','diagnostic_pipeline','hand_object_distances']]
    sc=modules[0];export=modules[5];m=load('surface_coverage',root)
    if sys.platform=='linux':
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(180,180))
    if a.action=='build':
        sc.require(a.receipt_sha256 is None,'build_receipt_not_allowed')
        report,files=m.build(a.workspace,a.workspace_sha256,a.distances,a.distance_sha256,a.case,*modules,purpose=a.purpose);export.publish(a.output,files,sc)
        result=dict(receipt_binding=sc.binding(files['files.json']),source_workspace_binding=report['source_workspace_binding'],candidates=[dict(id=c['id'],profiles=c['profiles'],collision_gate=c['collision_gate']) for c in report['candidates']],placement_ready=False)
    else:
        sc.require(a.receipt_sha256 is not None,'receipt_required')
        result=m.verify(a.output,a.receipt_sha256,a.workspace,a.workspace_sha256,a.distances,a.distance_sha256,a.case,*modules,purpose=a.purpose)
    print(sc.encode(result).decode(),end='')
if __name__=='__main__':main()
