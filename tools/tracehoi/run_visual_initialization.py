"""Build a CPU visual initial pose or verify its optimizer handoff."""
import argparse,importlib.util,json
from pathlib import Path
def load(root,n):
 s=importlib.util.spec_from_file_location(n,root/'src/foho/geometry'/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['build','verify'])
 for n in ['inputs','input-sha256','output','purpose']:p.add_argument('--'+n,required=True)
 p.add_argument('--receipt-sha256');a=p.parse_args();root=Path(__file__).resolve().parents[2];m=load(root,'visual_initialization');sc=load(root,'scene_candidates')
 if a.action=='build':
  sc.require(a.receipt_sha256 is None,'build_receipt_not_allowed');r,files=m.build(a.inputs,a.input_sha256,sc,purpose=a.purpose);load(root,'diagnostic_scene_export').publish(a.output,files,sc);out=dict(receipt_binding=sc.binding(files['files.json']),initialization_ready=r['initialization_ready'],optimizer_handoff_ready=r['optimizer_handoff_ready'],placement_ready=False)
 else:out=m.verify(a.output,a.receipt_sha256,a.inputs,a.input_sha256,sc,purpose=a.purpose)
 print(json.dumps(out,sort_keys=True))
if __name__=='__main__':main()
