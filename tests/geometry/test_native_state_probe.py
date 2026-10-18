import ast,copy,importlib.util,json,struct,tempfile,unittest,zlib
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
def module(n):
 s=importlib.util.spec_from_file_location(n,ROOT/'src/foho/geometry'/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=module('native_state_probe');review=module('scene_review');reader=module('scene_candidates')
N=512*512
PIPE=b'def transform_mesh_around_center_w_scale(mesh,T,scale):\n return mesh\ndef transform_hunyuan2moge(mesh,RT):\n return mesh\n'
HELP=b'def get_guidance_params(*args,**kwargs):\n return args\n'
H=SimpleNamespace(BACKEND_PINS=(m.pin(PIPE)['sha256'],m.pin(HELP)['sha256']))
class StateTests(unittest.TestCase):
 def pixels(self):
  rgb=bytes([11,22,33])*N;mask=bytearray(N);mask[123]=255;hand=bytearray(N);hand[234]=255;over=bytearray(N);over[345]=255
  return rgb,bytes(mask),bytes(hand),bytes(over)
 def fixture(self):
  rgb,mask,hand,over=self.pixels()
  files={'image.png':review.rgb_png(rgb),'object_mask.pgm':review.pgm(mask),'hand_mask.pgm':review.pgm(hand),'overlap_mask.pgm':review.pgm(over),'centered_state.json':m.encode(dict(schema='tracehoi.CenteredOptimizerState.v1',input_geometry='native_hamer',center_rule='axis_aligned_bbox_midpoint',contact_terms_used=False,scale=2.0)),'scene.html':b'<html>unchanged scene</html>','native_hand.ply':b'hand fixture','object.ply':b'object fixture','files.json':b'{}'}
  camera=SimpleNamespace(load_runtime=lambda folder,sha,r:(files,dict(case_id='test')))
  prior=m.encode(dict(schema='tracehoi.NativeCameraCPUPreflight.v1',passed=True,runtime_receipt_sha256='a'*64,raster_mask_exact=True))
  return ['unused','a'*64,PIPE,HELP,prior,camera,H,reader,review]
 def build(self,args=None):return m.build(*(args or self.fixture()),purpose=m.PURPOSE)
 def test_exact_foreground(self):
  args=self.pixels();r=m.conditioning_pixels(*args);self.assertEqual(r[492:496],b'\x0b\x16\x21\xff')
 def test_transparent_background_is_white_RGB(self):self.assertEqual(m.conditioning_pixels(*self.pixels())[:4],b'\xff\xff\xff\0')
 def test_no_hand_in_conditioning(self):self.assertEqual(m.conditioning_pixels(*self.pixels())[234*4+3],0)
 def test_no_ambiguous_in_conditioning(self):self.assertEqual(m.conditioning_pixels(*self.pixels())[345*4+3],0)
 def test_input_bytes_unchanged(self):
  p=self.pixels();before=copy.deepcopy(p);m.conditioning_pixels(*p);self.assertEqual(p,before)
 def test_empty_mask_refused(self):
  p=list(self.pixels());p[1]=bytes(N)
  with self.assertRaisesRegex(ValueError,'empty_or_full'):m.conditioning_pixels(*p)
 def test_full_mask_refused(self):
  p=list(self.pixels());p[1]=b'\xff'*N
  with self.assertRaisesRegex(ValueError,'empty_or_full'):m.conditioning_pixels(*p)
 def test_overlap_refused(self):
  p=list(self.pixels());p[2]=p[1]
  with self.assertRaisesRegex(ValueError,'support_overlap'):m.conditioning_pixels(*p)
 def test_nonbinary_mask_refused(self):
  p=list(self.pixels());p[1]=b'\x80'+p[1][1:]
  with self.assertRaisesRegex(ValueError,'binary_masks'):m.conditioning_pixels(*p)
 def test_wrong_dimensions_refused(self):
  p=list(self.pixels());p[0]=p[0][:-1]
  with self.assertRaisesRegex(ValueError,'shape'):m.conditioning_pixels(*p)
 def test_RGBA_roundtrip_standard_chunks(self):
  raw=m.conditioning_pixels(*self.pixels());png=m.rgba_png(raw);pos=8;payload=b''
  while pos<len(png):
   size=int.from_bytes(png[pos:pos+4],'big');name=png[pos+4:pos+8];data=png[pos+8:pos+8+size];self.assertEqual(zlib.crc32(name+data)&0xffffffff,int.from_bytes(png[pos+8+size:pos+12+size],'big'))
   if name==b'IHDR':self.assertEqual(struct.unpack('>IIBBBBB',data),(512,512,8,6,0,0,0))
   if name==b'IDAT':payload+=data
   pos+=12+size
  decoded=zlib.decompress(payload);self.assertEqual(b''.join(decoded[y*2049+1:(y+1)*2049] for y in range(512)),raw)
 def test_RGBA_size_bound(self):
  with self.assertRaisesRegex(ValueError,'rgba_shape'):m.rgba_png(b'bad')
 def test_changed_source_refused(self):
  with self.assertRaisesRegex(ValueError,'native_source_changed'):m.selected_functions(PIPE+b'\n',HELP,H)
 def test_changed_helper_refused(self):
  with self.assertRaisesRegex(ValueError,'native_source_changed'):m.selected_functions(PIPE,HELP+b'\n',H)
 def test_only_three_functions_selected(self):self.assertEqual(set(m.selected_functions(PIPE,HELP,H)),{'transform_mesh_around_center_w_scale','transform_hunyuan2moge','get_guidance_params'})
 def test_source_top_level_never_executed(self):
  raw=PIPE+b"raise RuntimeError('top-level executed')\n";h=SimpleNamespace(BACKEND_PINS=(m.pin(raw)['sha256'],m.pin(HELP)['sha256']));funcs=m.compile_functions(raw,HELP,h,None);self.assertEqual(funcs['transform_hunyuan2moge']('mesh',None),'mesh')
 def test_missing_function_refused(self):
  h=SimpleNamespace(BACKEND_PINS=(m.pin(b'pass')['sha256'],m.pin(HELP)['sha256']))
  with self.assertRaisesRegex(ValueError,'native_function_count'):m.selected_functions(b'pass',HELP,h)
 def test_placement_purpose_refused(self):
  with self.assertRaisesRegex(ValueError,'purpose_required'):m.build(*self.fixture(),purpose='placement')
 def test_prior_camera_failure_refused(self):
  a=self.fixture();j=json.loads(a[4]);j['passed']=False;a[4]=m.encode(j)
  with self.assertRaisesRegex(ValueError,'prior_camera_not_verified'):self.build(a)
 def test_prior_camera_other_inputs_refused(self):
  a=self.fixture();j=json.loads(a[4]);j['runtime_receipt_sha256']='b'*64;a[4]=m.encode(j)
  with self.assertRaisesRegex(ValueError,'prior_camera_not_verified'):self.build(a)
 def test_synthetic_prior_camera_refused(self):
  a=self.fixture();j=json.loads(a[4]);j['fixture_only']=True;a[4]=m.encode(j)
  with self.assertRaisesRegex(ValueError,'prior_camera_not_verified'):self.build(a)
 def test_no_latent_or_contact_claim(self):
  r,_=self.build();self.assertEqual(r['latent_policy']['status'],'unresolved');self.assertFalse(r['contact_terms_used']);self.assertFalse(r['rectified_flow_executed']);self.assertFalse(r['native_state_execution_verified']);self.assertFalse(r['backend_execution_ready'])
 def test_conditioning_counts(self):
  r,_=self.build();self.assertEqual(r['conditioning']['alpha_pixels'],1);self.assertEqual(r['conditioning']['excluded_hand_pixels'],1);self.assertEqual(r['conditioning']['excluded_ambiguous_pixels'],1)
 def test_output_receipt_and_originals(self):
  a=self.fixture();r,f=self.build(a);source=a[5].load_runtime(None,None,None)[0]
  for n in ['image.png','object_mask.pgm','native_hand.ply','object.ply','scene.html']:self.assertEqual(f[n],source[n])
  self.assertEqual(json.loads(f['files.json'])['files'],{n:m.pin(b) for n,b in f.items() if n!='files.json'})
 def test_build_verify_then_mutation_rejected(self):
  a=self.fixture();r,f=self.build(a)
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp).resolve()
   for n,b in f.items():(p/n).write_bytes(b)
   self.assertTrue(m.verify(p,m.pin(f['files.json'])['sha256'],*a,purpose=m.PURPOSE)['verified'])
   (p/'object_conditioning.png').write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'state_output_changed'):m.verify(p,m.pin(f['files.json'])['sha256'],*a,purpose=m.PURPOSE)
 def test_negative_scale_rejected(self):
  a=self.fixture();files=a[5].load_runtime(None,None,None)[0];s=json.loads(files['centered_state.json']);s['scale']=-1;files['centered_state.json']=m.encode(s)
  with self.assertRaisesRegex(ValueError,'hand_state_scale'):self.build(a)
 def test_UI_contains_no_native_success_claim(self):
  _,f=self.build();self.assertIn(b'Pending server',f['index.html']);self.assertIn(b'No native-state success is claimed',f['index.html']);self.assertIn(b'Joint-flow run',f['index.html'])
if __name__=='__main__':unittest.main()
