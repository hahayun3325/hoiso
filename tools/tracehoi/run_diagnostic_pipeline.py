"""Build, verify or inspect a portable saved-input diagnostic pipeline workspace."""
import argparse,importlib.util,sys
from pathlib import Path

def load(name,root):
    spec=importlib.util.spec_from_file_location(name,root/'src/foho/geometry'/(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['build','verify','inspect'])
    for n in ['workspace','case','purpose']:p.add_argument('--'+n,required=True)
    for n in ['package','package-sha256','workspace-sha256','reference','candidate']:p.add_argument('--'+n)
    a=p.parse_args();root=Path(__file__).resolve().parents[2]
    sc,render,viewer,records,ready,export,v,c,pipeline=[load(n,root) for n in ['scene_candidates','scene_review','hand_domain_review','mask_review_record','scene_readiness','diagnostic_scene_export','mask_validation','candidate_comparison','diagnostic_pipeline']]
    if sys.platform=='linux':
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(180,180))
    modules=(sc,render,viewer,records,ready,export,v,c)
    if a.action=='build':
        sc.require(a.package and a.package_sha256 and not a.workspace_sha256 and not a.candidate,'build_arguments')
        ref=sc.regular(a.reference,1024**2) if a.reference else None
        report,files=pipeline.build(a.package,a.package_sha256,a.case,*modules,reference_raw=ref,purpose=a.purpose)
        export.publish(a.workspace,files,sc);digest=sc.binding(files['workspace.json'])['sha256']
        result=pipeline.verify(a.workspace,digest,a.case,*modules,purpose=a.purpose)
    else:
        sc.require(a.workspace_sha256 and not a.package and not a.package_sha256 and not a.reference,'verify_arguments')
        if a.action=='verify':
            sc.require(a.candidate is None,'verify_does_not_select_candidate');result=pipeline.verify(a.workspace,a.workspace_sha256,a.case,*modules,purpose=a.purpose)
        else:
            result=pipeline.load_candidate(a.workspace,a.workspace_sha256,a.case,*modules,candidate_id=a.candidate,purpose=a.purpose)
            for role in ['hand','object']:result['scene'][role+'_mesh_binding']=sc.binding(result['scene'].pop(role+'_mesh_bytes'))
    print(sc.encode(result).decode(),end='')
if __name__=='__main__':main()
