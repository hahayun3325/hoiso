"""Build or verify a CPU centered-state bridge; no native optimizer execution."""
import argparse,importlib.util,json
from pathlib import Path
def load(root,n):
 s=importlib.util.spec_from_file_location(n,root/'src/foho/geometry'/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['build','verify'])
 for n in ['source','source-sha256','prediction','output','purpose']:p.add_argument('--'+n,required=True)
 p.add_argument('--receipt-sha256');a=p.parse_args();root=Path(__file__).resolve().parents[2];m=load(root,'optimizer_bridge');sc=load(root,'scene_candidates');v=load(root,'visual_initialization');raw=sc.regular(Path(a.prediction),1024**2)
 if a.action=='build':
  sc.require(a.receipt_sha256 is None,'build_receipt_not_allowed');r,files=m.build(a.source,a.source_sha256,raw,sc,v,purpose=a.purpose);load(root,'diagnostic_scene_export').publish(a.output,files,sc);out=dict(receipt_binding=m.pin(files['files.json']),bridge_complete=True,initialization_ready=True,backend_execution_ready=False,placement_ready=False)
 else:out=m.verify(a.output,a.receipt_sha256,a.source,a.source_sha256,raw,sc,v,purpose=a.purpose)
 print(json.dumps(out,sort_keys=True))
if __name__=='__main__':main()
