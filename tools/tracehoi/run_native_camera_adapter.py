"""Build/verify a data adapter, or explicitly run its CPU-only native preflight."""
import argparse,importlib.util,json,traceback
from pathlib import Path
def load(root,n):
 s=importlib.util.spec_from_file_location(n,root/'src/foho/geometry'/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['build','verify','cpu-preflight'])
 for n in ['source','source-sha256','output','purpose']:p.add_argument('--'+n,required=True)
 p.add_argument('--receipt-sha256');p.add_argument('--backend-source');a=p.parse_args();root=Path(__file__).resolve().parents[2]
 m=load(root,'native_camera_adapter');reader=load(root,'scene_candidates');m.require(a.purpose==m.PURPOSE,'native_camera_adapter_purpose_required')
 if a.action=='cpu-preflight':
  progress={}
  try:
   result=m.native_cpu_preflight(a.source,a.source_sha256,reader,progress=progress)
  except Exception as exc:
   result=dict(schema='tracehoi.NativeCameraCPUPreflight.v1',passed=False,device='cpu',runtime_receipt_sha256=a.source_sha256,diagnostics=progress,error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
   with Path(a.output).open('xb') as f:f.write(m.encode(result))
   raise
  with Path(a.output).open('xb') as f:f.write(m.encode(result))
 else:
  h=load(root,'native_handoff');raw=reader.regular(a.backend_source,2*1024**2);args=(a.source,a.source_sha256,raw,h,reader)
  if a.action=='build':
   m.require(a.receipt_sha256 is None,'build_receipt_not_allowed');r,files=m.build(*args,purpose=a.purpose);load(root,'diagnostic_scene_export').publish(a.output,files,reader)
   result=dict(receipt_binding=m.pin(files['files.json']),adapter_complete=True,initialization_ready=True,backend_execution_ready=False,placement_ready=False)
  else:result=m.verify(a.output,a.receipt_sha256,*args,purpose=a.purpose)
 print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
