import importlib.util,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
def load(n):
 s=importlib.util.spec_from_file_location(n,ROOT/'src/foho/geometry'/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('native_conditioning');reader=load('scene_candidates');review=load('scene_review')
class Tests(unittest.TestCase):
 def mask(self,box=(100,120,300,220)):
  a=bytearray(512*512);x0,y0,x1,y1=box
  for y in range(y0,y1+1):a[y*512+x0:y*512+x1+1]=b'\xff'*(x1-x0+1)
  return bytes(a)
 def source(self):
  raw=b'class Hunyuan3DDiTFlowMatchingPipeline_main:\n def __call__(self):\n  self.prepare_latents(batch_size,dtype,device,generator)\n'
  vae=b'class ShapeVAE:\n def __init__(self):pass\n def forward(self):pass\n def latents2mesh(self):pass\n'
  sources={'models_vae.py.txt':vae,'preprocessors.py.txt':b'pass\n','schedulers.py.txt':b'pass\n','config.yaml.txt':b'config\n'}
  return raw,sources,SimpleNamespace(BACKEND_PINS=[m.pin(raw)['sha256']])
 def contract(self,raw=None,sources=None,h=None):
  r,s,ha=self.source();raw=r if raw is None else raw;sources=s if sources is None else sources;h=ha if h is None else h
  with patch.dict(m.PINS,{n:m.pin(b) for n,b in sources.items()},clear=True):return m.source_contract(raw,sources,h)
 def fixture(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name).resolve();raw,sources,h=self.source();mask=self.mask();files={'object_mask.pgm':review.pgm(mask),'image.png':b'image','object_conditioning.png':b'condition','files.json':b'old','index.html':b'old','state_probe.json':b'old','scene.html':b'scene','hand_initial.ply':b'hand'}
  prev=dict(case_id='case',conditioning=dict(binding=m.pin(b'condition')))
  state=SimpleNamespace(PURPOSE='native_state_probe',build=lambda *a,**kw:(prev,files));native=dict(schema='tracehoi.NativeStateCPUPreflight.v1',passed=True,runtime_receipt_sha256='digest',conditioning_binding=m.pin(b'condition'))
  for n,b in sources.items():(root/n).write_bytes(b)
  args=[root,'digest',raw,b'helper',b'camera',m.encode(native),root,None,h,reader,review,state]
  return root,args,sources
 def build(self,args,sources):
  with patch.dict(m.PINS,{n:m.pin(b) for n,b in sources.items()},clear=True):return m.build(*args,purpose=m.PURPOSE)
 def test_crop_native_half_open(self):self.assertEqual(m.recenter_contract(self.mask())['native_crop_xyxy_exclusive'],[100,120,300,220])
 def test_landscape_center(self):
  c=m.recenter_contract(self.mask());self.assertEqual(c['resize_wh'],[434,217]);self.assertEqual(c['paste_xy'],[39,147])
 def test_portrait_center(self):self.assertEqual(m.recenter_contract(self.mask((120,100,220,300)))['resize_wh'],[217,434])
 def test_empty(self):
  with self.assertRaisesRegex(ValueError,'mask_empty'):m.recenter_contract(bytes(512*512))
 def test_binary(self):
  with self.assertRaisesRegex(ValueError,'mask_shape_binary'):m.recenter_contract(bytes([1])*512*512)
 def test_shape(self):
  with self.assertRaises(ValueError):m.recenter_contract(b'')
 def test_line(self):
  with self.assertRaisesRegex(ValueError,'mask_line'):m.recenter_contract(self.mask((120,100,120,300)))
 def test_bad_borders(self):
  for b in [True,-.1,1,float('nan'),float('inf'),'x']:
   with self.assertRaisesRegex(ValueError,'border_ratio'):m.recenter_contract(self.mask(),b)
 def test_full_mask(self):self.assertEqual(m.recenter_contract(bytes([255])*512*512)['resize_wh'],[435,435])
 def test_shape_latent_contract(self):
  r=self.contract();self.assertFalse(r['mesh_encoder_exposed']);self.assertFalse(r['joint_loop_supplies_saved_latent']);self.assertFalse(r['model_latent_sampled']);self.assertEqual(r['model_latent_shape'],[1,3072,64])
 def test_pipeline_changed(self):
  with self.assertRaisesRegex(ValueError,'pipeline_changed'):self.contract(raw=b'changed')
 def test_latent_keyword_refused(self):
  raw,s,h=self.source();raw=raw.replace(b'generator)',b'generator, latents=saved)');h.BACKEND_PINS=[m.pin(raw)['sha256']]
  with self.assertRaisesRegex(ValueError,'joint_latent_entry_changed'):self.contract(raw,s,h)
 def test_vae_encoder_refused(self):
  raw,s,h=self.source();s['models_vae.py.txt']+=b' def encode(self):pass\n'
  with self.assertRaisesRegex(ValueError,'vae_interface_changed'):self.contract(raw,s,h)
 def test_native_module_rejects_unpinned(self):
  with self.assertRaisesRegex(ValueError,'native_module_not_admitted'):m.native_module('preprocessors',b'raise Exception()')
 def test_vae_never_importable(self):
  with self.assertRaises(ValueError):m.native_module('models_vae',b'pass')
 def test_missing_source(self):
  root,a,s=self.fixture();(root/'schedulers.py.txt').unlink()
  with self.assertRaises(FileNotFoundError):self.build(a,s)
 def test_tampered_source(self):
  root,a,s=self.fixture();(root/'schedulers.py.txt').write_bytes(b'bad')
  with self.assertRaisesRegex(ValueError,'conditioning_source_changed'):self.build(a,s)
 def test_native_state_failure_refused(self):
  root,a,s=self.fixture();n=json.loads(a[5]);n['passed']=False;a[5]=m.encode(n)
  with self.assertRaisesRegex(ValueError,'prior_state_not_verified'):self.build(a,s)
 def test_native_state_fixture_refused(self):
  root,a,s=self.fixture();n=json.loads(a[5]);n['fixture_only']=True;a[5]=m.encode(n)
  with self.assertRaisesRegex(ValueError,'prior_state_not_verified'):self.build(a,s)
 def test_native_state_binding_refused(self):
  root,a,s=self.fixture();n=json.loads(a[5]);n['conditioning_binding']=m.pin(b'wrong');a[5]=m.encode(n)
  with self.assertRaisesRegex(ValueError,'prior_state_not_verified'):self.build(a,s)
 def test_scope(self):
  root,a,s=self.fixture();r,f=self.build(a,s)
  for k in ['native_conditioning_execution_verified','backend_execution_ready','rectified_flow_executed','contact_terms_used','placement_ready']:self.assertIs(r[k],False)
  self.assertTrue(r['native_state_execution_verified']);self.assertEqual(f['hand_initial.ply'],b'hand');self.assertEqual(f['object_conditioning.png'],b'condition')
 def test_purpose_refused(self):
  with self.assertRaisesRegex(ValueError,'native_conditioning_purpose_required'):m.build(*([None]*12),purpose='placement')
 def test_verified_packet(self):
  root,a,s=self.fixture();r,f=self.build(a,s);out=root/'output';out.mkdir()
  for n,b in f.items():(out/n).write_bytes(b)
  with patch.dict(m.PINS,{n:m.pin(b) for n,b in s.items()},clear=True):self.assertTrue(m.verify(out,m.pin(f['files.json'])['sha256'],*a,purpose=m.PURPOSE)['verified'])
 def test_changed_output_refused(self):
  root,a,s=self.fixture();r,f=self.build(a,s);out=root/'output';out.mkdir()
  for n,b in f.items():(out/n).write_bytes(b)
  (out/'scene.html').write_bytes(b'bad')
  with patch.dict(m.PINS,{n:m.pin(b) for n,b in s.items()},clear=True),self.assertRaisesRegex(ValueError,'conditioning_output_changed'):m.verify(out,m.pin(f['files.json'])['sha256'],*a,purpose=m.PURPOSE)
 def test_viewer_pending_and_escaping(self):
  root,a,s=self.fixture();r,f=self.build(a,s);r['extra']='</script><h1>injected';html=m.viewer(r,b'RGB',b'RGBA');self.assertNotIn('</script><h1>',html);self.assertIn('Pending server',html);self.assertIn('Synthetic test',html);self.assertNotIn('https://',html)
if __name__=='__main__':unittest.main(verbosity=2)
