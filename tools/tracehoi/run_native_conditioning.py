"""Prepare or verify native image conditioning; explicit CPU-only probe, no model."""
import argparse,importlib.util,json,traceback
from pathlib import Path
def load(root,n):
 s=importlib.util.spec_from_file_location(n,root/'src/foho/geometry'/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['build','verify','cpu-preflight'])
 for n in ['source','source-sha256','output','purpose','backend-source','helper-source','camera-result','state-result','sources']:p.add_argument('--'+n,required=True)
 p.add_argument('--receipt-sha256');p.add_argument('--conditioning');p.add_argument('--artifacts');a=p.parse_args();root=Path(__file__).resolve().parents[2]
 m=load(root,'native_conditioning');reader=load(root,'scene_candidates');m.require(a.purpose==m.PURPOSE,'native_conditioning_purpose_required')
 h=load(root,'native_handoff');camera=load(root,'native_camera_adapter');review=load(root,'scene_review');state=load(root,'native_state_probe')
 raw=reader.regular(a.backend_source,2*1024**2);helper=reader.regular(a.helper_source,1024**2);prior=reader.regular(a.camera_result,1024**2);prior_state=reader.regular(a.state_result,1024**2)
 args=(a.source,a.source_sha256,raw,helper,prior,prior_state,a.sources,camera,h,reader,review,state)
 if a.action=='cpu-preflight':
  progress={};condition_binding=None
  try:
   m.require(a.conditioning and a.artifacts,'conditioning_and_artifacts_required')
   condition_binding=m.pin(reader.regular(Path(a.conditioning)/'object_conditioning.png',2*1024**2))
   result,files=m.cpu_preflight(*args[:7],a.conditioning,*args[7:],progress=progress)
   load(root,'diagnostic_scene_export').publish(a.artifacts,files,reader)
  except Exception as exc:
   result=dict(schema='tracehoi.NativeConditioningCPUPreflight.v1',passed=False,device='cpu',runtime_receipt_sha256=a.source_sha256,conditioning_binding=condition_binding,diagnostics=progress,error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
   with Path(a.output).open('xb') as f:f.write(m.encode(result))
   raise
  with Path(a.output).open('xb') as f:f.write(m.encode(result))
 else:
  if a.action=='build':
   m.require(a.receipt_sha256 is None,'build_receipt_not_allowed');r,files=m.build(*args,purpose=a.purpose);load(root,'diagnostic_scene_export').publish(a.output,files,reader)
   result=dict(receipt_binding=m.pin(files['files.json']),prepared=True,initialization_ready=True,backend_execution_ready=False,placement_ready=False)
  else:result=m.verify(a.output,a.receipt_sha256,*args,purpose=a.purpose)
 print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
