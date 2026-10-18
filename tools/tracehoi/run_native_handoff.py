"""Build or verify an opt-in native handoff packet without native imports."""
import argparse
import importlib.util
import json
from pathlib import Path

def load(root,name):
    spec=importlib.util.spec_from_file_location(name,root/'src/foho/geometry'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['build','verify'])
    for n in ['source','source-sha256','backend-source','guidance-source','output','purpose']:
        p.add_argument('--'+n,required=True)
    p.add_argument('--receipt-sha256')
    a=p.parse_args();root=Path(__file__).resolve().parents[2]
    m=load(root,'native_handoff');reader=load(root,'scene_candidates');bridge=load(root,'optimizer_bridge')
    args=(a.source,a.source_sha256,reader.regular(Path(a.backend_source),2*1024**2),
          reader.regular(Path(a.guidance_source),2*1024**2),reader,bridge)
    if a.action=='build':
        m.require(a.receipt_sha256 is None,'build_receipt_not_allowed')
        r,files=m.build(*args,purpose=a.purpose)
        load(root,'diagnostic_scene_export').publish(a.output,files,reader)
        result=dict(receipt_binding=m.pin(files['files.json']),native_handoff_complete=True,
                    initialization_ready=True,backend_execution_ready=False,placement_ready=False)
    else:
        result=m.verify(a.output,a.receipt_sha256,*args,purpose=a.purpose)
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
