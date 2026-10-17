"""Inspect stage readiness or prepare diagnostic data from a bound saved scene."""
import argparse,importlib.util,json,os,sys
from pathlib import Path

def load(name,root):
 s=importlib.util.spec_from_file_location(name,root/'src/foho/geometry'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['report','prepare']);p.add_argument('manifest');p.add_argument('--sha256',required=True);p.add_argument('--case',required=True);p.add_argument('--review-dir',required=True);p.add_argument('--files-sha256',required=True);p.add_argument('--record');p.add_argument('--stage',choices=['diagnostic_export','mask_revision_planning','placement']);p.add_argument('--candidate');p.add_argument('--output');a=p.parse_args()
 root=Path(__file__).resolve().parents[2];sc=load('scene_candidates',root);renderer=load('scene_review',root);viewer=load('hand_domain_review',root);records=load('mask_review_record',root);ready=load('scene_readiness',root)
 if sys.platform=='linux':
  import resource
  resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(60,60))
 raw=sc.regular(a.record,128*1024) if a.record else None
 args=(a.manifest,a.sha256,a.case,a.review_dir,a.files_sha256,sc,renderer,viewer,records)
 if a.action=='prepare':
  sc.require(a.stage and not a.output,'prepare_arguments')
  result=ready.prepare_stage(*args,stage=a.stage,candidate=a.candidate,record_raw=raw)
  if 'scene' in result:
   for role in ['hand','object']:result['scene'][role+'_mesh_binding']=sc.binding(result['scene'].pop(role+'_mesh_bytes'))
  print(sc.encode(result).decode(),end='');return
 sc.require(a.output and not a.stage and not a.candidate,'report_arguments')
 report=ready.evaluate(*args,record_raw=raw);_,form=records.build(a.manifest,a.sha256,a.case,a.review_dir,a.files_sha256,sc,renderer,viewer)
 out=Path(a.output).absolute();sc.require('..' not in out.parts and not os.path.lexists(out),'new_output_required')
 for parent in [*reversed(out.parent.parents),out.parent]:sc.require(parent.is_dir() and not parent.is_symlink(),'output_parent_route')
 files={'readiness.json':sc.encode(report),'index.html':ready.html(report),'TRACEHOI_MASK_REVIEW_RECORD_Z2x7Pf4Z.html':form['index.html']}
 receipt=dict(schema='tracehoi.SceneReadinessFiles.v1',manifest_binding=report['context']['manifest_binding'],files={n:sc.binding(b) for n,b in files.items()});files['files.json']=sc.encode(receipt)
 out.mkdir(mode=0o700)
 for n,b in files.items():
  with (out/n).open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
  sc.require(sc.regular(out/n,8*1024**2)==b,'output_readback')
 fd=os.open(str(out),os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
 print(json.dumps(dict(complete=True,review_state=report['review']['state'],next_action=report['next_action'],placement_ready=False,files=len(files)),sort_keys=True))
if __name__=='__main__':main()
