import ast,copy,importlib.util,json,math,struct,tempfile,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[2]
def load(n):
 s=importlib.util.spec_from_file_location(n,root/'src/foho/geometry'/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('native_camera_adapter');ri=load('runtime_inputs');reader=load('scene_candidates')
C=dict(image_size_wh=[48,32],K_integer_pixel_centers=[[35.,0.,13.3],[0.,42.,19.7],[0.,0.,1.]],pixel_centers='integer_xy',scene_to_opencv=[[1,0,0],[0,-1,0],[0,0,-1]])
class Array(list):
 def new_tensor(self,v):return v
 def __sub__(self,v):return Array([a-b for a,b in zip(self,v)])
class Torch:
 float32='float32'
 @staticmethod
 def tensor(v,**kw):return v
class Camera:
 def __init__(self,**kw):self.kw=kw
 def transform_points_screen(self,p,**kw):self.screen_kw=kw;return Array(p)
class Checks(unittest.TestCase):
 def test_numeric_roundtrip(self):
  v=[[i+.25,-i-.5] for i in range(21)];self.assertEqual(m.numeric_array(ri.numeric_npy([x for row in v for x in row],(21,2)),(21,2)),v)
 def test_npy_version_rejected(self):
  with self.assertRaisesRegex(ValueError,'version'):m.numeric_array(b'pickle',(21,2))
 def test_npy_shape_rejected(self):
  with self.assertRaisesRegex(ValueError,'type_shape'):m.numeric_array(ri.numeric_npy([0]*42,(21,2)),(4,4))
 def test_npy_trailing_bytes(self):
  with self.assertRaisesRegex(ValueError,'size'):m.numeric_array(ri.numeric_npy([0]*42,(21,2))+b'x',(21,2))
 def test_npy_nonfinite(self):
  raw=ri.numeric_npy([0]*42,(21,2));raw=raw[:-4]+struct.pack('<f',float('nan'))
  with self.assertRaisesRegex(ValueError,'nonfinite'):m.numeric_array(raw,(21,2))
 def test_npy_object_type_refused(self):
  raw=ri.numeric_npy([0]*42,(21,2)).replace(b'<f4',b'|O8')
  with self.assertRaisesRegex(ValueError,'type_shape'):m.numeric_array(raw,(21,2))
 def test_guidance_returns_fresh_values(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t).resolve()/'k.npy';b=ri.numeric_npy([1,2]*21,(21,2));p.write_bytes(b);l=m.NumericGuidance(p,m.pin(b),reader)
   a=l.load(p);a['mano_2d_kps'][0][0]=9;self.assertEqual(l.load(p)['mano_2d_kps'][0][0],1)
 def test_guidance_changed_bytes(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t).resolve()/'k.npy';b=ri.numeric_npy([1,2]*21,(21,2));p.write_bytes(b);l=m.NumericGuidance(p,m.pin(b),reader);p.write_bytes(b+b'x')
   with self.assertRaisesRegex(ValueError,'binding_changed'):l.load(p)
 def test_guidance_other_path(self):
  l=m.NumericGuidance('/a',{},reader)
  with self.assertRaisesRegex(ValueError,'path_changed'):l.load('/b')
 def test_guidance_symlink(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t).resolve()/'x';b=ri.numeric_npy([1,2]*21,(21,2));p.write_bytes(b);q=Path(t).resolve()/'k';q.symlink_to(p);l=m.NumericGuidance(q,m.pin(b),reader)
   with self.assertRaises(ValueError):l.load(q)
 def test_camera_contract_nonsquare(self):
  c=m.camera_contract(C);self.assertEqual(c['image_size_hw'],[32,48]);self.assertEqual(c['principal_point_edge'],[13.8,20.2])
 def test_camera_nonfinite(self):
  c=copy.deepcopy(C);c['K_integer_pixel_centers'][0][0]=float('nan')
  with self.assertRaisesRegex(ValueError,'finite'):m.camera_contract(c)
 def test_camera_skew_refused(self):
  c=copy.deepcopy(C);c['K_integer_pixel_centers'][0][1]=1
  with self.assertRaisesRegex(ValueError,'form'):m.camera_contract(c)
 def test_camera_wrong_frame(self):
  c=dict(C,scene_to_opencv=[[1,0,0],[0,1,0],[0,0,1]])
  with self.assertRaisesRegex(ValueError,'frame'):m.camera_contract(c)
 def test_camera_size_refused(self):
  with self.assertRaisesRegex(ValueError,'size'):m.camera_contract(dict(C,image_size_wh=[0,512]))
 def test_projection_axes_and_depth(self):
  self.assertEqual(m.project([[0,0,-2],[2,2,-2]],C),[[13.3,19.7],[48.3,-22.3]])
 def test_projection_behind_camera_refused(self):
  with self.assertRaisesRegex(ValueError,'point_front'):m.project([[0,0,1]],C)
 def test_factory_cpu_and_intrinsics(self):
  c=m.make_camera(C,Torch,Camera);self.assertEqual(c.kw['device'],'cpu');self.assertFalse(c.kw['in_ndc']);self.assertEqual(c.kw['R'],[[[-1,0,0],[0,1,0],[0,0,-1]]]);self.assertEqual(c.kw['principal_point'],[[13.8,20.2]])
 def test_screen_offset_does_not_touch_depth(self):
  c=m.make_camera(C,Torch,Camera);self.assertEqual(c.transform_points_screen([13.8,20.2,.2]),[13.3,19.7,.2])
 def test_screen_axis_override_refused(self):
  with self.assertRaisesRegex(ValueError,'xyflip'):m.make_camera(C,Torch,Camera).transform_points_screen([0,0,0],with_xyflip=False)
 def test_purpose_refusal(self):
  with self.assertRaisesRegex(ValueError,'purpose_required'):m.build(None,None,None,None,None,purpose='placement')
 def test_source_seam_changed_refused(self):
  class H:
   @staticmethod
   def patch_source(raw):return b'def f(*, _tracehoi_handoff=None, **kwargs,):\n pass\n'
  with self.assertRaisesRegex(ValueError,'seam_changed'):m.patch_source(b'',H)
 def test_private_overlay_preserves_legacy_branch(self):
  raw=b"def f(*, _tracehoi_handoff=None, **kwargs,):\n hamer4guid = np.load(hamer_for_guid_path, allow_pickle=True).item()\n"
  class H:
   @staticmethod
   def patch_source(raw):return raw
  out=m.patch_source(raw,H);ast.parse(out);self.assertIn(b'else np.load',out);self.assertIn(b'_tracehoi_numeric.load',out);self.assertNotIn(b'_tracehoi_numeric',raw)
 def test_module_has_no_native_top_level_imports(self):
  tree=ast.parse((root/'src/foho/geometry/native_camera_adapter.py').read_bytes())
  names=[n.names[0].name for n in tree.body if isinstance(n,ast.Import)]
  self.assertNotIn('torch',names);self.assertNotIn('numpy',names);self.assertNotIn('pytorch3d',names)
class RasterRecovery(unittest.TestCase):
 def test_legacy_diagonal_ties_reproduced(self):
  f=m.raster_fixture(legacy=True);self.assertEqual(f['edge_tie_pixels_xy'],[[5,7],[6,8],[7,9],[8,10],[20,13],[21,14],[22,15],[23,16]])
 def test_recovery_margin_over_float_noise(self):
  f=m.raster_fixture();self.assertGreater(f['minimum_edge_margin_px'],.08);self.assertEqual(f['edge_tie_pixels_xy'],[])
 def test_expected_mask_unchanged(self):
  a=m.raster_fixture();b=m.raster_fixture(legacy=True);self.assertEqual(a['expected_mask'],b['expected_mask']);self.assertEqual(sum(map(sum,a['expected_mask'])),32)
 def test_half_pixel_x_error_is_detected(self):
  f=m.raster_fixture();g=m.raster_fixture(shift_xy=(.5,0));self.assertFalse(m.raster_diagnostics(g['expected_mask'],f)['mask_exact'])
 def test_half_pixel_y_error_is_detected(self):
  f=m.raster_fixture();g=m.raster_fixture(shift_xy=(0,-.5));self.assertFalse(m.raster_diagnostics(g['expected_mask'],f)['mask_exact'])
 def test_edge_diagnosis_does_not_accept_holes(self):
  f=m.raster_fixture(legacy=True);a=copy.deepcopy(f['expected_mask'])
  for x,y in f['edge_tie_pixels_xy']:a[y][x]=False
  d=m.raster_diagnostics(a,f);self.assertFalse(d['mask_exact']);self.assertTrue(d['all_mismatches_on_shared_edges']);self.assertEqual(len(d['missing_pixels_xy']),8)
 def test_off_edge_failure_distinguished(self):
  f=m.raster_fixture(legacy=True);a=copy.deepcopy(f['expected_mask']);a[7][6]=False
  d=m.raster_diagnostics(a,f);self.assertFalse(d['all_mismatches_on_shared_edges']);self.assertEqual(d['missing_pixels_xy'],[[6,7]])
 def test_false_positive_diagnosed(self):
  f=m.raster_fixture();a=copy.deepcopy(f['expected_mask']);a[0][0]=True;d=m.raster_diagnostics(a,f);self.assertFalse(d['mask_exact']);self.assertEqual(d['extra_pixels_xy'],[[0,0]])
 def test_malformed_observation_rejected(self):
  with self.assertRaisesRegex(ValueError,'diagnostic_shape'):m.raster_diagnostics([[True]],m.raster_fixture())
 def test_fixture_world_to_integer_projection(self):
  f=m.raster_fixture();a=m.project(f['vertices'],C)
  for actual,expected in zip(a,[(4.75,6.625),(8.25,6.625),(8.25,10.125),(4.75,10.125),(19.75,12.625),(23.25,12.625),(23.25,16.125),(19.75,16.125)]):
   for x,y in zip(actual,expected):self.assertAlmostEqual(x,y,places=12)
if __name__=='__main__':unittest.main()
