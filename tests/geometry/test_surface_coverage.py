import importlib.util,math,random,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load(n):
    s=importlib.util.spec_from_file_location(n,ROOT/'src/foho/geometry'/(n+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('surface_coverage');d=load('hand_object_distances')
T=((0.,0.,1.),(1.,0.,1.),(0.,1.,1.))
class Coverage(unittest.TestCase):
    def test_area(self):self.assertEqual(m.area(T),.5)
    def test_area_translation(self):self.assertEqual(m.area(tuple(tuple(x+7 for x in v) for v in T)),.5)
    def test_area_scaling(self):self.assertEqual(m.area(tuple(tuple(x*3 for x in v) for v in T)),4.5)
    def test_area_orientation(self):self.assertEqual(m.area(T),m.area(T[::-1]))
    def test_degenerate_area(self):self.assertEqual(m.area(((0,0,0),)*3),0)
    def test_analytic_plane_bound(self):
        samples=[(p,1.,(p[0],p[1],0)) for p in T];lo,hi=m.envelope(T,samples,0)
        self.assertLessEqual(lo,1);self.assertGreaterEqual(hi,1)
    def test_point_object_envelope(self):
        q=(0,0,0);s=[(p,math.dist(p,q),q) for p in T];lo,hi=m.envelope(T,s,0)
        self.assertAlmostEqual(hi,math.sqrt(2));self.assertLessEqual(lo,1)
    def test_guard_widens(self):
        s=[(T[0],1.,(0,0,0))];a=m.envelope(T,s,0);b=m.envelope(T,s,.1)
        self.assertLessEqual(b[0],a[0]);self.assertAlmostEqual(b[1],a[1]+.1)
    def test_more_samples_tighten(self):
        s=[(p,1.,(p[0],p[1],0)) for p in T];a=m.envelope(T,s[:1],0);b=m.envelope(T,s,0)
        self.assertGreaterEqual(b[0],a[0]);self.assertLessEqual(b[1],a[1])
    def test_interior_points_against_exhaustive(self):
        rng=random.Random(364);obj=[tuple(tuple(rng.uniform(-1,1) for _ in range(3)) for _ in range(3)) for _ in range(10)]
        def nearest(p):
            x=min((d.closest(p,t) for t in obj),key=lambda x:x[0]);return (p,math.sqrt(x[0]),x[1])
        for _ in range(30):
            tri=[tuple(rng.uniform(-2,2) for _ in range(3)) for _ in range(3)];center=tuple(sum(v[k] for v in tri)/3 for k in range(3));lo,hi=m.envelope(tri,[nearest(p) for p in tri+[center]],1e-12)
            for _ in range(40):
                ws=[rng.random() for _ in range(3)];p=tuple(sum(ws[j]*tri[j][k] for j in range(3))/sum(ws) for k in range(3));dist=nearest(p)[1]
                self.assertGreaterEqual(dist,lo);self.assertLessEqual(dist,hi)
    def test_within_equality(self):self.assertEqual(m.classify(1,2,2),'within_bound')
    def test_lower_equality_unresolved(self):self.assertEqual(m.classify(1,2,1),'unresolved')
    def test_outside(self):self.assertEqual(m.classify(1,2,.9),'outside_bound')
    def test_zero_threshold(self):self.assertEqual(m.classify(0,0,0),'within_bound')
    def test_invalid_intervals(self):
        for args in [(2,1,1),(-1,1,1),(0,1,-1),(0,math.inf,1),(0,1,math.nan)]:
            with self.assertRaises(ValueError):m.classify(*args)
    def test_area_weighted_not_face_count(self):
        rows=[dict(area=9,lower=0,upper=.1),dict(area=1,lower=2,upper=3)];s=m.coverage(rows,1)
        self.assertEqual(s['area_fraction_lower'],.9);self.assertEqual(s['area_fraction_upper'],.9)
    def test_unresolved_preserved(self):
        rows=[dict(area=2,lower=0,upper=.1),dict(area=3,lower=0,upper=2),dict(area=5,lower=3,upper=4)];s=m.coverage(rows,1)
        self.assertEqual(s['area_fraction_lower'],.2);self.assertEqual(s['area_fraction_upper'],.5);self.assertEqual(s['unresolved_area_fraction'],.3)
    def test_zero_area_does_not_vote(self):
        s=m.coverage([dict(area=0,lower=0,upper=0),dict(area=1,lower=3,upper=4)],1);self.assertEqual(s['area_fraction_upper'],0)
    def test_zero_total_refused(self):
        with self.assertRaisesRegex(ValueError,'positive_hand_area'):m.coverage([dict(area=0,lower=0,upper=0)],1)
    def test_negative_area_refused(self):
        with self.assertRaisesRegex(ValueError,'face_area'):m.coverage([dict(area=-1,lower=0,upper=0)],1)
    def test_monotone_thresholds(self):
        rows=[dict(area=i+1,lower=i/2,upper=i+1) for i in range(10)];ss=[m.coverage(rows,t) for t in range(12)]
        for k in ['area_fraction_lower','area_fraction_upper']:self.assertEqual([s[k] for s in ss],sorted(s[k] for s in ss))
    def test_numerical_inputs_refused(self):
        for samples,guard in [([],0),([(T[0],math.nan,(0,0,0))],0),([(T[0],1,(0,0,0))],-1)]:
            with self.assertRaises(ValueError):m.envelope(T,samples,guard)
    def test_purpose_refused(self):
        with self.assertRaisesRegex(ValueError,'purpose_required'):m.build(None,None,None,None,None,*([None]*10),purpose='placement')
    def test_verify_purpose_refused(self):
        with self.assertRaisesRegex(ValueError,'purpose_required'):m.verify(None,None,None,None,None,None,None,purpose='placement')
    def test_html_escaping(self):
        raw=m.html({'marker':'</script><img src=x>'});self.assertNotIn(b'</script><img',raw);self.assertIn(b'\\u003c/script',raw);self.assertIn(b"connect-src 'none'",raw)
if __name__=='__main__':unittest.main()
