import copy,importlib.util,math,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load(n):
 s=importlib.util.spec_from_file_location(n,ROOT/'src/foho/geometry'/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('adaptive_surface_map');a=load('adaptive_coverage');c=load('surface_coverage')
V=[(0.,0.,0.),(1.,0.,1.),(0.,1.,1.)];F=[(0,1,2)];OV=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)]
class Plane:
 def nearest(self,p):return dict(distance=abs(p[2]),point=[p[0],p[1],0.],object_triangle=0,barycentric=[1-p[0]-p[1],p[0],p[1]])
def source():
 r=a.refine(V,F,[dict(face_index=0,area=c.area(V),lower=0.,upper=1.000000001)],Plane(),c,.25,1e-9);r.update(id='test',hand_binding=dict(bytes=1,sha256='x'),collision_gate='blocked_transverse_crossing');return r
def locate(r=None):return m.locate(r or source(),V,F,OV,F,a,c,.25)
class SurfaceMap(unittest.TestCase):
 def test_reconstruct_root(self):self.assertEqual(m.triangle(V,F,0,'',a),tuple(V))
 def test_reconstruct_child(self):self.assertEqual(m.triangle(V,F,0,'23',a),a.split(a.split(V)[2])[3])
 def test_area_by_depth(self):
  for path in ['0','13','222']:self.assertAlmostEqual(c.area(m.triangle(V,F,0,path,a)),c.area(V)/4**len(path))
 def test_bad_paths(self):
  for path in ['4','-1','0000',None]:
   with self.assertRaisesRegex(ValueError,'cell_path'):m.triangle(V,F,0,path,a)
 def test_bad_face(self):
  for f in [-1,1,True]:
   with self.assertRaisesRegex(ValueError,'cell_face'):m.triangle(V,F,f,'',a)
 def test_partition_complete(self):self.assertEqual(set(m.partition(source()['leaves'],1)),{0})
 def test_missing_face_refused(self):
  with self.assertRaisesRegex(ValueError,'incomplete_partition'):m.partition(source()['leaves'],2)
 def test_duplicate_refused(self):
  rows=source()['leaves'];rows.append(rows[0])
  with self.assertRaisesRegex(ValueError,'duplicate_cell'):m.partition(rows,1)
 def test_missing_child_refused(self):
  with self.assertRaisesRegex(ValueError,'incomplete_partition'):m.partition(source()['leaves'][1:],1)
 def test_overlapping_partition_refused(self):
  # Weights sum to one but '0' overlaps '00'; missing children elsewhere.
  rows=[dict(face_index=0,path=p) for p in ['0','00','01','02','03','1','2']]
  with self.assertRaisesRegex(ValueError,'overlapping_cells'):m.partition(rows,1)
 def test_query_identity(self):
  r=locate();self.assertTrue(r['witnesses'])
  for w in r['witnesses']:
   leaf=r['leaves'][w['leaf_index']];self.assertEqual((leaf['face_index'],leaf['path']),(w['query']['face_index'],w['query']['path']));self.assertEqual(w['object_triangle_vertices'],[list(x) for x in OV])
 def test_saved_numbers_preserved(self):
  s=source();r=locate(s);self.assertEqual(r['leaves'],s['leaves']);self.assertEqual(r['stage'],s['stages'][-1]);self.assertEqual(r['collision_gate'],s['collision_gate'])
 def test_geometry_preserved(self):
  before=copy.deepcopy((V,F,OV));r=locate();self.assertEqual((V,F,OV),before);self.assertEqual(r['vertices'],V);self.assertEqual(r['faces'],F);self.assertIs(r['accepted'],False)
 def test_root_has_no_new_witness(self):
  s=source();s=a.refine(V,F,[dict(face_index=0,area=c.area(V),lower=.5,upper=1.)],Plane(),c,.25,1e-9)|{k:s[k] for k in ['id','hand_binding','collision_gate']};self.assertEqual(locate(s)['witnesses'],[])
 def test_missing_query_refused(self):
  s=source();key=(s['leaves'][0]['face_index'],s['leaves'][0]['path']);s['queries']=[q for q in s['queries'] if (q['face_index'],q['path'])!=key]
  with self.assertRaisesRegex(ValueError,'missing_leaf_query'):locate(s)
 def test_duplicate_query_refused(self):
  s=source();s['queries'].append(s['queries'][0])
  with self.assertRaisesRegex(ValueError,'duplicate_query'):locate(s)
 def test_centroid_mismatch_refused(self):
  s=source();p=s['leaves'][0]['path'];next(q for q in s['queries'] if q['path']==p)['centroid'][0]+=1e-3
  with self.assertRaisesRegex(ValueError,'query_cell_centroid'):locate(s)
 def test_bad_object_triangle_refused(self):
  s=source();p=s['leaves'][0]['path'];next(q for q in s['queries'] if q['path']==p)['object_triangle']=1
  with self.assertRaisesRegex(ValueError,'query_object_face'):locate(s)
 def test_classification_mismatch_refused(self):
  s=source();s['leaves'][0]['state']='fake'
  with self.assertRaisesRegex(ValueError,'cell_classification'):locate(s)
 def test_nan_area_refused(self):
  s=source();s['leaves'][0]['area']=math.nan
  with self.assertRaisesRegex(ValueError,'cell_area'):locate(s)
 def test_build_purpose_refused(self):
  with self.assertRaisesRegex(ValueError,'purpose_required'):m.build(*([None]*9),purpose='placement')
 def test_verify_purpose_refused(self):
  with self.assertRaisesRegex(ValueError,'purpose_required'):m.verify(None,None,purpose='placement')
 def test_html_injection_escaped(self):
  h=m.html(dict(value='</script><img>'),b'');self.assertNotIn(b'</script><img>',h);self.assertIn(b'\\u003c/script',h)
 def test_offline_companions_and_limits(self):
  h=m.html({},b'');self.assertIn(b"connect-src 'none'",h);self.assertIn(b'href="adaptive.html"',h);self.assertIn(b'href="reference_annotation.html"',h);self.assertIn(b'No physical contact',h);self.assertIn(b'Inherited K4 bounds',h)
if __name__=='__main__':unittest.main()
