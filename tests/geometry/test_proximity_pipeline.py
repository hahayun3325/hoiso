import copy,importlib.util,math,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('proximity',Path(__file__).resolve().parents[2]/'src/foho/geometry/proximity_pipeline.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def fixture():return dict(object_bbox_diagonal=1.,numerical_guard=1e-9,candidates=[dict(id='primary',accepted=False,faces=[dict(lower=.1,upper=.2,area=.5,point=[1.,2.,3.],object_triangle=7)],profiles=[dict(threshold=.15,counts={'unresolved':1})])],placement_ready=False,source_binding={'sha256':'a'*64})
class Proximity(unittest.TestCase):
 def setUp(self):self.expected=fixture();self.saved=copy.deepcopy(self.expected)
 def rejected(self,text):
  with self.assertRaisesRegex(ValueError,text):m.compare_bounds(self.saved,self.expected)
 def test_equal(self):
  r=m.compare_bounds(self.saved,self.expected);self.assertEqual(r['different_endpoints'],0);self.assertEqual(r['endpoint_values_checked'],2)
 def test_last_bit_lower(self):
  self.saved['candidates'][0]['faces'][0]['lower']=math.nextafter(.1,1.);self.assertEqual(m.compare_bounds(self.saved,self.expected)['different_endpoints'],1)
 def test_last_bit_upper(self):
  self.saved['candidates'][0]['faces'][0]['upper']=math.nextafter(.2,0.);self.assertGreater(m.compare_bounds(self.saved,self.expected)['maximum_endpoint_difference'],0)
 def test_large_difference(self):self.saved['candidates'][0]['faces'][0]['upper']+=1e-8;self.rejected('endpoint_difference')
 def test_nan(self):self.saved['candidates'][0]['faces'][0]['upper']=math.nan;self.rejected('endpoint')
 def test_infinite(self):self.saved['candidates'][0]['faces'][0]['upper']=math.inf;self.rejected('endpoint')
 def test_negative(self):self.saved['candidates'][0]['faces'][0]['lower']=-1.;self.rejected('endpoint')
 def test_boolean_is_not_number(self):self.saved['candidates'][0]['faces'][0]['lower']=False;self.rejected('type')
 def test_integer_type_preserved(self):self.saved['candidates'][0]['faces'][0]['object_triangle']=7.;self.rejected('type')
 def test_area_exact(self):self.saved['candidates'][0]['faces'][0]['area']=math.nextafter(.5,1);self.rejected('exact_field')
 def test_witness_exact(self):self.saved['candidates'][0]['faces'][0]['point'][0]=math.nextafter(1.,2);self.rejected('exact_field')
 def test_triangle_index_exact(self):self.saved['candidates'][0]['faces'][0]['object_triangle']=8;self.rejected('exact_field')
 def test_candidate_identity_exact(self):self.saved['candidates'][0]['id']='other';self.rejected('exact_field')
 def test_acceptance_refused(self):self.saved['candidates'][0]['accepted']=True;self.rejected('exact_field')
 def test_placement_refused(self):self.saved['placement_ready']=True;self.rejected('exact_field')
 def test_binding_exact(self):self.saved['source_binding']['sha256']='b'*64;self.rejected('exact_field')
 def test_profile_counts_exact(self):self.saved['candidates'][0]['profiles'][0]['counts']['unresolved']=0;self.rejected('exact_field')
 def test_threshold_exact(self):self.saved['candidates'][0]['profiles'][0]['threshold']=math.nextafter(.15,1);self.rejected('exact_field')
 def test_changed_classification_refused(self):
  self.expected['candidates'][0]['profiles'][0]['threshold']=.2;self.saved=copy.deepcopy(self.expected);self.saved['candidates'][0]['faces'][0]['upper']=math.nextafter(.2,1);self.rejected('classification_changed')
 def test_missing_key(self):del self.saved['placement_ready'];self.rejected('keys')
 def test_added_key(self):self.saved['extra']=0;self.rejected('keys')
 def test_wrong_face_count(self):self.saved['candidates'][0]['faces']=[];self.rejected('length')
 def test_zero_diagonal(self):self.expected['object_bbox_diagonal']=0.;self.rejected('numeric_policy')
 def test_guard_caps_tolerance(self):
  self.expected['numerical_guard']=1e-14;self.saved=copy.deepcopy(self.expected);self.assertEqual(m.compare_bounds(self.saved,self.expected)['endpoint_tolerance'],1e-14/1024)
 def test_purpose_required(self):
  with self.assertRaisesRegex(ValueError,'purpose_required'):m.build(None,None,None,None,None,None,None,purpose='placement')
 def test_verify_purpose_required(self):
  with self.assertRaisesRegex(ValueError,'purpose_required'):m.verify(None,None,None,None,None,None,None,None,None,purpose='placement')
 def test_html_safe(self):
  b=m.html({'note':'</script><img src=x>'},b'img');self.assertNotIn(b'</script><img',b);self.assertIn(b'\\u003c/script',b);self.assertIn(b"connect-src 'none'",b)
 def test_report_order_does_not_rewrite_viewer(self):
  source={'z':[{'upper':.2,'lower':.1}],'a':False};parsed={'a':False,'z':[{'lower':math.nextafter(.1,1.),'upper':.2}]}
  got=m.ordered_like(parsed,source);self.assertEqual(list(got),['z','a']);self.assertEqual(list(got['z'][0]),['upper','lower']);self.assertEqual(got,parsed)
 def test_companion_links(self):
  b=m.html({},b'img')
  for n in ['scene.html','distances.html','coverage.html','reference_annotation.html']:self.assertIn(('href="'+n+'"').encode(),b)
if __name__=='__main__':unittest.main()
