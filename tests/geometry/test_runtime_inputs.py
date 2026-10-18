import importlib.util,json,math,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def load(n):
 s=importlib.util.spec_from_file_location(n,R/'src/foho/geometry'/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
M=load('runtime_inputs');V=load('visual_initialization');reader=load('scene_candidates')
class RuntimeInputs(unittest.TestCase):
 def identity(self):return [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
 def triangle(self):return V.ply([[0,0,1],[1,0,1],[0,1,1]],[[0,1,2]])
 def camera(self):return dict(K=[[1024,0,255.5],[0,1024,255.5],[0,0,1]],image_size=[512,512],camera_frame='x_right_y_down_z_forward',scene_frame='N7_PLY_x_right_y_up_z_backward')
 def observation(self):return dict(intrinsics_normalized=[[2,0,.5],[0,2,.5],[0,0,1]],prior_scene_reused=False,prior_camera_reused=False,prior_alignment_transforms_reused=False)
 def grid(self):return [0,0,1,1,0,1,0,1,1,1,1,1],[True]*4,[1]*4,[2,2]
 def test_binary_mask_roundtrip(self):self.assertEqual(M.pgm(M.pgm_bytes([1,0,1,0],[2,2]),[2,2]),[True,False,True,False])
 def test_mask_nonbinary_refused(self):
  with self.assertRaisesRegex(ValueError,'mask_not_binary'):M.pgm(b'P5\n2 2\n255\n'+bytes([0,255,1,0]),[2,2])
 def test_mask_dimensions_refused(self):
  with self.assertRaisesRegex(ValueError,'mask_layout'):M.pgm(M.pgm_bytes([1]*4,[2,2]),[1,4])
 def test_mask_truncation_refused(self):
  with self.assertRaises(ValueError):M.pgm(M.pgm_bytes([1]*4,[2,2])[:-1],[2,2])
 def test_numeric_npy_layout(self):self.assertEqual(V.npy(M.numeric_npy([1,2,3,4],[2,2]),'<f4',[2,2]),[1,2,3,4])
 def test_numeric_shape_refused(self):
  with self.assertRaisesRegex(ValueError,'numeric_array'):M.numeric_npy([1,2],[3])
 def test_numeric_nan_refused(self):
  with self.assertRaises(ValueError):M.numeric_npy([float('nan')],[1])
 def test_numeric_infinite_refused(self):
  with self.assertRaises(ValueError):M.numeric_npy([float('inf')],[1])
 def test_camera_half_pixel(self):self.assertEqual(M.camera_check(self.camera(),self.observation())['K_integer_pixel_centers'][0][2],255.5)
 def test_camera_old_principal_point_refused(self):
  c=self.camera();c['K'][0][2]=256
  with self.assertRaisesRegex(ValueError,'fresh_camera_mismatch'):M.camera_check(c,self.observation())
 def test_camera_wrong_frame_refused(self):
  c=self.camera();c['scene_frame']='old'
  with self.assertRaisesRegex(ValueError,'camera_frame'):M.camera_check(c,self.observation())
 def test_camera_old_scene_refused(self):
  o=self.observation();o['prior_scene_reused']=True
  with self.assertRaisesRegex(ValueError,'old_scene_reuse'):M.camera_check(self.camera(),o)
 def test_camera_invalid_focal_refused(self):
  c=self.camera();c['K'][0][0]=-1
  with self.assertRaises(ValueError):M.camera_check(c,self.observation())
 def test_object_identity(self):self.assertEqual(M.object_check(self.triangle(),self.triangle(),self.identity(),reader)['max_coordinate_error'],0)
 def test_object_translation(self):
  T=self.identity();T[0][3]=2;v,f=reader.mesh(self.triangle());b=V.ply([M.transform(p,T) for p in v],f);self.assertEqual(M.object_check(self.triangle(),b,T,reader)['vertices'],3)
 def test_object_wrong_transform_refused(self):
  T=self.identity();T[0][3]=2
  with self.assertRaisesRegex(ValueError,'object_transform_mismatch'):M.object_check(self.triangle(),self.triangle(),T,reader)
 def test_object_reflection_refused(self):
  T=self.identity();T[0][0]=-1
  with self.assertRaisesRegex(ValueError,'object_not_proper_similarity'):M.object_check(self.triangle(),self.triangle(),T,reader)
 def test_object_anisotropic_refused(self):
  T=self.identity();T[0][0]=2
  with self.assertRaisesRegex(ValueError,'object_not_proper_similarity'):M.object_check(self.triangle(),self.triangle(),T,reader)
 def test_object_topology_refused(self):
  v,f=reader.mesh(self.triangle());b=V.ply(v,[[0,2,1]])
  with self.assertRaisesRegex(ValueError,'object_topology'):M.object_check(self.triangle(),b,self.identity(),reader)
 def test_scene_winding_and_frame(self):
  v,f,r,ids=M.scene_mesh(*self.grid());self.assertEqual(v[3],[1,-1,-1]);self.assertEqual(f,[[0,2,1],[1,2,3]]);self.assertEqual(ids,[0,1,2,3]);self.assertFalse(r['closed_surface'])
 def test_scene_invalid_pixel_excluded(self):
  p,v,l,s=self.grid();v[3]=False;verts,f,r,ids=M.scene_mesh(p,v,l,s);self.assertEqual(len(f),1);self.assertNotIn(3,ids)
 def test_scene_ambiguous_pixel_excluded(self):
  p,v,l,s=self.grid();l[3]=3;verts,f,r,ids=M.scene_mesh(p,v,l,s);self.assertEqual(len(f),1);self.assertNotIn(3,ids)
 def test_scene_class_seam_excluded(self):
  p,v,l,s=self.grid();l[3]=2;verts,f,r,ids=M.scene_mesh(p,v,l,s);self.assertEqual(len(f),1);self.assertEqual(r['excluded_label_seams'],1)
 def test_scene_depth_jump_excluded(self):
  p,v,l,s=self.grid();p[-1]=2;verts,f,r,ids=M.scene_mesh(p,v,l,s);self.assertEqual(len(f),1);self.assertEqual(r['excluded_depth_jumps'],1)
 def test_scene_invalid_point_refused(self):
  p,v,l,s=self.grid();p[2]=0
  with self.assertRaisesRegex(ValueError,'scene_point'):M.scene_mesh(p,v,l,s)
 def test_scene_no_surface_refused(self):
  p,v,l,s=self.grid();v=[False]*4
  with self.assertRaisesRegex(ValueError,'empty_scene_surface'):M.scene_mesh(p,v,l,s)
 def test_placement_purpose_refused(self):
  with self.assertRaisesRegex(ValueError,'runtime_inputs_purpose_required'):M.build(None,None,None,None,purpose='placement')
 def test_source_receipt_tamper_refused(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t).resolve();(p/'inputs.json').write_bytes(b'{}')
   with self.assertRaisesRegex(ValueError,'source_receipt_hash'):M.read_sources(p,'0'*64,reader)
if __name__=='__main__':unittest.main()
