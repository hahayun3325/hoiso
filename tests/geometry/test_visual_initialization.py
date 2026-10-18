import ast,importlib.util,io,json,math,struct,tempfile,unittest,zipfile
from pathlib import Path
s=importlib.util.spec_from_file_location('visual_initialization',Path(__file__).resolve().parents[2]/'src/foho/geometry/visual_initialization.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class VisualInitialization(unittest.TestCase):
 def setUp(self):
  self.xyz=[[.05*math.sin(i),.05*math.cos(i),.012*math.sin(i*.7)] for i in range(21)];self.K=[[700,0,255.5],[0,700,255.5],[0,0,1]];self.t=[.07,.03,1.8];self.xy=m.project([m.add(p,self.t) for p in self.xyz],self.K);self.box=[200,200,330,330]
 def test_synthetic_camera_recovery(self):
  f=m.fit_camera(self.xyz,self.xy,[1]*21,self.K,self.box);self.assertLess(f['joint_rmse_px'],1e-4);self.assertLess(m.norm([a-b for a,b in zip(f['translation'],self.t)]),1e-4)
 def test_rotation_prior_preserves_geometry(self):
  R=m.rodrigues([.2,-.1,.4]);a=self.xyz[0];b=self.xyz[1];self.assertAlmostEqual(m.norm([x-y for x,y in zip(a,b)]),m.norm([x-y for x,y in zip(m.mv(R,a),m.mv(R,b))]),12)
 def test_rotation_zero(self):self.assertEqual(m.rodrigues([0,0,0]),[[1,0,0],[0,1,0],[0,0,1]])
 def test_projection_scale_gauge(self):
  p=[m.add(v,self.t) for v in self.xyz];a=m.project(p,self.K);b=m.project([[2.6*x for x in v] for v in p],self.K);self.assertLess(max(abs(x-y) for u,v in zip(a,b) for x,y in zip(u,v)),1e-10)
 def test_duplicate_targets_share_weight(self):self.assertEqual(m.weight_targets([[1,2],[1,2],[1,2]],[.9]*3),[.3]*3)
 def test_invalid_confidence(self):
  with self.assertRaisesRegex(ValueError,'confidence'):m.fit_camera(self.xyz,self.xy,[float('nan')]*21,self.K,self.box)
 def test_nan_geometry(self):
  self.xyz[0][0]=float('nan')
  with self.assertRaisesRegex(ValueError,'joint_values'):m.fit_camera(self.xyz,self.xy,[1]*21,self.K,self.box)
 def test_bad_joint_count(self):
  with self.assertRaisesRegex(ValueError,'joint_count'):m.fit_camera(self.xyz[:-1],self.xy,[1]*21,self.K,self.box)
 def test_bad_box(self):
  with self.assertRaisesRegex(ValueError,'box'):m.fit_camera(self.xyz,self.xy,[1]*21,self.K,[4,2,1,3])
 def test_nonpositive_depth(self):
  with self.assertRaisesRegex(ValueError,'nonpositive'):m.project([[0,0,0]],self.K)
 def test_box_is_containment_not_stretch(self):
  p=[0,0,0]+self.t;w=[1]*21;a=m.objective(p,self.xyz,self.xy,w,self.K,self.box);b=m.objective(p,self.xyz,self.xy,w,self.K,[0,0,512,512]);self.assertEqual(a[0],b[0])
 def test_outside_box_penalty(self):
  p=[0,0,0]+self.t;a=m.objective(p,self.xyz,self.xy,[1]*21,self.K,self.box)[0];b=m.objective(p,self.xyz,self.xy,[1]*21,self.K,[0,0,10,10])[0];self.assertGreater(b,a)
 def test_huber_resists_one_outlier(self):
  self.xy[20]=[500,500];f=m.fit_camera(self.xyz,self.xy,[1]*21,self.K,self.box);self.assertLess(f['joint_median_px'],1)
 def test_linear_solver(self):self.assertEqual(m.solve([[2,1],[1,3]],[4,7]),[1.,2.])
 def test_singular_refused(self):
  with self.assertRaisesRegex(ValueError,'singular'):m.solve([[0,0],[0,0]],[1,1])
 def test_raster_perspective_depth(self):
  r=m.raster_depth([[0,0,1],[4,0,2],[0,4,2]],[[0,1,2]],[[1,0,0],[0,1,0],[0,0,1]],[4,4]);self.assertAlmostEqual(r[5],2);self.assertAlmostEqual(r[1],4/3)
 def test_raster_nearest_surface(self):
  v=[[0,0,1],[2,0,1],[0,2,1],[0,0,2],[4,0,2],[0,4,2]];r=m.raster_depth(v,[[0,1,2],[3,4,5]],[[1,0,0],[0,1,0],[0,0,1]],[4,4]);self.assertEqual(r[0],1)
 def test_scale_recovery(self):
  r={i:2. for i in range(1024)};o={i:5. for i in r};g=m.scale_from_depth(r,o,64);self.assertEqual(g['scale'],2.5);self.assertFalse(g['metric_scale_verified'])
 def test_sparse_scale_refused(self):
  with self.assertRaisesRegex(ValueError,'insufficient_shared'):m.scale_from_depth({0:2},{0:3},512)
 def test_tile_weight_resists_dense_outlier(self):
  r={i:2. for i in range(4096)};o={i:5. for i in r}
  for y in range(8):
   for x in range(8):o[y*64+x]=200
  self.assertEqual(m.scale_from_depth(r,o,64)['scale'],2.5)
 def test_npy_layout_refused(self):
  h=str(dict(descr='<i8',fortran_order=False,shape=(1,))).encode();raw=b'\x93NUMPY\x01\x00'+struct.pack('<H',len(h))+h+struct.pack('<q',3)
  with self.assertRaisesRegex(ValueError,'npy_layout'):m.npy(raw,'<f4',[1])
 def test_npy_truncated_refused(self):
  h=str(dict(descr='<f4',fortran_order=False,shape=(1,))).encode();raw=b'\x93NUMPY\x01\x00'+struct.pack('<H',len(h))+h
  with self.assertRaisesRegex(ValueError,'npy_length'):m.npy(raw,'<f4',[1])
 def test_final_placement_purpose_refused(self):
  with self.assertRaisesRegex(ValueError,'visual_initialization_purpose_required'):m.build(None,None,None,purpose='placement')
 def test_objective_has_no_contact_arguments(self):
  import inspect
  self.assertEqual(list(inspect.signature(m.fit_camera).parameters),['joints','xy','conf','K','box']);self.assertEqual(list(inspect.signature(m.scale_from_depth).parameters),['rendered','observed','width'])
if __name__=='__main__':unittest.main()
