import copy,importlib.util,math,random,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load(n):
 s=importlib.util.spec_from_file_location(n,ROOT/'src/foho/geometry'/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('adaptive_coverage');c=load('surface_coverage')
class Plane:
 def nearest(self,p):return dict(distance=abs(p[2]),point=[p[0],p[1],0.],object_triangle=0,barycentric=[1.,0.,0.])
V=[(0.,0.,0.),(1.,0.,1.),(0.,1.,1.)];F=[(0,1,2)]
def rows():return [dict(face_index=0,area=c.area(V),lower=0.,upper=1.000000001)]
def run(**kw):return m.refine(V,F,rows(),Plane(),c,.25,1e-9,**kw)
class Adaptive(unittest.TestCase):
 def test_split_conserves_area(self):self.assertAlmostEqual(sum(c.area(t) for t in m.split(V)),c.area(V),15)
 def test_split_centers_inside(self):
  for t in m.split(V):
   for x,y,z in t:self.assertGreaterEqual(x,0);self.assertGreaterEqual(y,0);self.assertLessEqual(x+y,1);self.assertEqual(z,x+y)
 def test_known_planar_fraction_bracketed(self):
  r=run()
  for s in r['stages']:self.assertLessEqual(s['area_fraction_lower'],.0625);self.assertGreaterEqual(s['area_fraction_upper'],.0625)
 def test_uncertainty_shrinks(self):self.assertLess(run()['stages'][-1]['unresolved_area_fraction'],run()['stages'][0]['unresolved_area_fraction'])
 def test_nested_stages(self):
  a=run()['stages']
  for x,y in zip(a,a[1:]):self.assertLessEqual(x['area_fraction_lower'],y['area_fraction_lower']);self.assertGreaterEqual(x['area_fraction_upper'],y['area_fraction_upper'])
 def test_area_conservation(self):
  r=run();self.assertAlmostEqual(sum(x['area'] for x in r['leaves']),c.area(V),14)
 def test_leaf_path_partition(self):
  paths=[x['path'] for x in run()['leaves']]
  for a in paths:
   for b in paths:
    if a!=b:self.assertFalse(b.startswith(a))
 def test_deterministic(self):self.assertEqual(run(),run())
 def test_zero_depth(self):self.assertEqual(run(max_depth=0)['queries'],[]);self.assertEqual(len(run(max_depth=0)['stages']),1)
 def test_insufficient_budget(self):self.assertEqual(run(max_queries=3)['queries'],[]);self.assertEqual(run(max_queries=3)['stop_reason'],'query_budget')
 def test_one_split_budget(self):r=run(max_queries=4);self.assertEqual(len(r['queries']),4);self.assertEqual(len(r['leaves']),4)
 def test_query_budget(self):
  for n in [0,1,3,4,7,8,15,32]:self.assertLessEqual(len(run(max_queries=n)['queries']),n)
 def test_resolved_not_queried(self):
  r=rows();r[0].update(lower=.5,upper=1.)
  got=m.refine(V,F,r,Plane(),c,.25,1e-9);self.assertEqual(got['queries'],[]);self.assertEqual(got['stop_reason'],'resolved')
 def test_zero_area_not_queried(self):
  vv=V+[V[0]];ff=F+[(0,0,0)];rr=rows()+[dict(face_index=1,area=0.,lower=0.,upper=1.)]
  got=m.refine(vv,ff,rr,Plane(),c,.25,1e-9);self.assertFalse(any(q['face_index']==1 for q in got['queries']))
 def test_root_order_refused(self):
  r=rows();r[0]['face_index']=2
  with self.assertRaisesRegex(ValueError,'root_identity'):m.refine(V,F,r,Plane(),c,.25,1e-9)
 def test_negative_area_refused(self):
  r=rows();r[0]['area']=-1.
  with self.assertRaisesRegex(ValueError,'root_identity'):m.refine(V,F,r,Plane(),c,.25,1e-9)
 def test_limits(self):
  for kw in [dict(max_depth=4),dict(max_depth=True),dict(max_queries=2049),dict(max_queries=-1)]:
   with self.assertRaisesRegex(ValueError,'limits'):run(**kw)
 def test_invalid_threshold(self):
  with self.assertRaisesRegex(ValueError,'input'):m.refine(V,F,rows(),Plane(),c,math.nan,1e-9)
 def test_child_envelopes_contain_sampled_distances(self):
  r=run();rng=random.Random(4)
  for leaf in r['leaves']:
   tri=V
   for digit in leaf['path']:tri=m.split(tri)[int(digit)]
   for _ in range(12):
    a,b=rng.random(),rng.random()
    if a+b>1:a,b=1-a,1-b
    z=(1-a-b)*tri[0][2]+a*tri[1][2]+b*tri[2][2]
    self.assertLessEqual(leaf['lower'],abs(z)+1e-14);self.assertGreaterEqual(leaf['upper'],abs(z)-1e-14)
 def test_child_bounds_inherit_parent(self):
  r=run();self.assertTrue(all(x['lower']>=0 and x['upper']<=rows()[0]['upper'] for x in r['leaves']))
 def test_fully_covered(self):
  r=m.refine(V,F,rows(),Plane(),c,2.,1e-9);self.assertEqual(r['stages'][-1]['area_fraction_lower'],1.)
 def test_purpose_refused(self):
  with self.assertRaisesRegex(ValueError,'purpose_required'):m.build(None,None,None,None,None,None,None,purpose='placement')
 def test_verify_purpose_refused(self):
  with self.assertRaisesRegex(ValueError,'purpose_required'):m.verify(None,None,None,None,None,None,None,None,None,purpose='placement')
 def fixture(self):return dict(numerical_guard=1e-9,threshold=.25,candidates=[dict(accepted=False,leaves=[dict(lower=.1,upper=.2,state='within_bound')],queries=[dict(object_triangle=0,distance=.15)])])
 def test_roundoff_allowed(self):
  e=self.fixture();s=copy.deepcopy(e);s['candidates'][0]['leaves'][0]['upper']=math.nextafter(.2,0);self.assertEqual(m.compare(s,e,c)['different_values'],1)
 def test_numeric_mutation_refused(self):
  e=self.fixture();s=copy.deepcopy(e);s['candidates'][0]['leaves'][0]['upper']+=1e-6
  with self.assertRaisesRegex(ValueError,'numeric'):m.compare(s,e,c)
 def test_exact_gate_and_triangle(self):
  e=self.fixture()
  for edit in ['accepted','object_triangle']:
   s=copy.deepcopy(e)
   if edit=='accepted':s['candidates'][0]['accepted']=True
   else:s['candidates'][0]['queries'][0]['object_triangle']=1
   with self.assertRaisesRegex(ValueError,'exact'):m.compare(s,e,c)
 def test_changed_classification_refused(self):
  e=self.fixture();e['threshold']=.2;s=copy.deepcopy(e);s['candidates'][0]['leaves'][0]['upper']=math.nextafter(.2,1)
  with self.assertRaisesRegex(ValueError,'classification'):m.compare(s,e,c)
 def test_safe_html(self):
  h=m.html(dict(value='</script><img>'),b'');self.assertNotIn(b'</script><img>',h);self.assertIn(b'\\u003c/script',h);self.assertIn(b'reference_annotation.html',h)
if __name__=='__main__':unittest.main()

