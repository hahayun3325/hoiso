import copy,importlib.util,math,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[2]
def load(n):
 s=importlib.util.spec_from_file_location(n,root/'src/foho/geometry'/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('optimizer_bridge')
class Bridge(unittest.TestCase):
 def setUp(self):
  self.v=[[0.,0.,0.],[2.,0.,0.],[0.,4.,1.],[.1,.2,.3]];self.M=[[0.,-2.,0.,3.],[2.,0.,0.,4.],[0.,0.,2.,5.],[0,0,0,1]];self.pin=m.pin(b'native');self.state=m.make_state(self.v,self.M,self.pin)
 def apply(self):return m.apply_state(self.v,self.state,input_geometry='native_hamer',geometry_binding=self.pin)
 def test_centered_roundtrip(self):
  expected=m.direct(self.v,self.M);self.assertLess(max(abs(a-b) for p,q in zip(self.apply(),expected) for a,b in zip(p,q)),1e-12)
 def test_bbox_center_not_mean(self):self.assertEqual(m.center(self.v),[1,2,.5])
 def test_center_compensation(self):self.assertEqual(self.state['translation'],[-2,4,5.5])
 def test_identity(self):
  I=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]];s=m.make_state(self.v,I,self.pin);self.assertEqual(s['translation'],[0,0,0]);self.assertLess(max(abs(a-b) for p,q in zip(m.apply_state(self.v,s,input_geometry='native_hamer',geometry_binding=self.pin),self.v) for a,b in zip(p,q)),1e-15)
 def test_double_transform_refused(self):
  with self.assertRaisesRegex(ValueError,'ownership'):m.apply_state(self.v,self.state,input_geometry='scene_mesh',geometry_binding=self.pin)
 def test_geometry_binding_refused(self):
  with self.assertRaisesRegex(ValueError,'binding'):m.apply_state(self.v,self.state,input_geometry='native_hamer',geometry_binding=m.pin(b'changed'))
 def test_center_change_refused(self):
  self.v[0][0]=-1
  with self.assertRaisesRegex(ValueError,'center_changed'):self.apply()
 def test_frame_refused(self):
  self.state['output_frame']='camera'
  with self.assertRaisesRegex(ValueError,'frame'):self.apply()
 def test_schema_refused(self):
  self.state['schema']='other'
  with self.assertRaisesRegex(ValueError,'ownership'):self.apply()
 def test_negative_scale_refused(self):
  self.state['scale']=-1
  with self.assertRaisesRegex(ValueError,'positive_scale'):self.apply()
 def test_zero_scale_refused(self):
  self.state['scale']=0
  with self.assertRaisesRegex(ValueError,'positive_scale'):self.apply()
 def test_interior_vertex_change_refused(self):
  self.v[3][0]+=.01
  with self.assertRaisesRegex(ValueError,'native_vertices_changed'):self.apply()
 def test_nan_translation(self):
  self.state['translation'][0]=float('nan')
  with self.assertRaisesRegex(ValueError,'translation'):self.apply()
 def test_non_unit_quaternion(self):
  with self.assertRaisesRegex(ValueError,'unit_quaternion'):m.from_quat([2.,0.,0.,0.])
 def test_quaternion_wxyz_order(self):
  self.assertEqual(m.from_quat([0.,1.,0.,0.]),[[1.,0.,0.],[0.,-1.,0.],[0.,0.,-1.]])
 def test_quaternion_identity(self):self.assertEqual(m.quat([[1,0,0],[0,1,0],[0,0,1]]),[1.,0.,0.,0.])
 def test_quaternion_pi_x(self):self.assertEqual(m.quat([[1,0,0],[0,-1,0],[0,0,-1]]),[0.,1.,0.,0.])
 def test_quaternion_pi_y(self):self.assertEqual(m.quat([[-1,0,0],[0,1,0],[0,0,-1]]),[0.,0.,1.,0.])
 def test_quaternion_pi_z(self):self.assertEqual(m.quat([[-1,0,0],[0,-1,0],[0,0,1]]),[0.,0.,0.,1.])
 def test_general_quaternion_roundtrip(self):
  q=[.5,-.5,.5,-.5];R=m.from_quat(q);self.assertEqual(m.quat(R),q)
 def test_shear_refused(self):
  self.M[0][0]=1
  with self.assertRaisesRegex(ValueError,'proper_rotation'):m.decompose(self.M)
 def test_reflection_refused(self):
  self.M[2][2]=-2
  with self.assertRaisesRegex(ValueError,'proper_rotation'):m.decompose(self.M)
 def test_anisotropic_refused(self):
  self.M[2][2]=3
  with self.assertRaisesRegex(ValueError,'proper_rotation'):m.decompose(self.M)
 def test_affine_row_refused(self):
  self.M[3][3]=2
  with self.assertRaisesRegex(ValueError,'affine_row'):m.decompose(self.M)
 def test_nan_matrix_refused(self):
  self.M[1][0]=float('nan')
  with self.assertRaisesRegex(ValueError,'matrix_shape'):m.decompose(self.M)
 def test_empty_geometry(self):
  with self.assertRaisesRegex(ValueError,'points'):m.center([])
 def test_nonfinite_geometry(self):
  with self.assertRaisesRegex(ValueError,'points'):m.center([[float('inf'),0,0]])
 def test_no_model_or_contact_execution(self):
  self.assertFalse(self.state['contact_terms_used']);self.assertFalse(self.state['backend_wired']);self.assertEqual(self.state['phase1_initialization'],'bypass_to_preserve_visual_initial_pose')
 def test_final_placement_refused(self):
  with self.assertRaisesRegex(ValueError,'purpose_required'):m.build(None,None,None,None,None,purpose='placement')
 def test_source_static_only(self):
  raw=b'raise RuntimeError("must not execute")\ndef helper(x):\n return x\n';r=m.inspect_source(raw);self.assertEqual(r['functions'][0]['name'],'helper');self.assertFalse(r['source_executed'])
 def test_source_call_census(self):
  r=m.inspect_source(b'get_guidance_params(phase=2)\nscheduler.step(x)\n');self.assertEqual(len(r['calls']),2)
 def test_source_size_refused(self):
  with self.assertRaisesRegex(ValueError,'source_cap'):m.inspect_source(b' '*(2*1024**2+1))
 def test_bad_source_syntax(self):
  with self.assertRaises(SyntaxError):m.inspect_source(b'def !')
if __name__=='__main__':unittest.main()
