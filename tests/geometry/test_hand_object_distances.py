import importlib.util,math,random,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('hod',Path(__file__).resolve().parents[2]/'src/foho/geometry/hand_object_distances.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
T=((0.,0.,0.),(1.,0.,0.),(0.,1.,0.))
class Distances(unittest.TestCase):
    def witness(self,p,t):
        d,q,b=m.closest(p,t);self.assertAlmostEqual(sum(b),1,12);self.assertGreaterEqual(min(b),0)
        for k in range(3):self.assertAlmostEqual(q[k],sum(b[i]*t[i][k] for i in range(3)),12)
        self.assertAlmostEqual(d,math.dist(p,q)**2,12);return d,q,b
    def test_interior(self):self.assertAlmostEqual(self.witness((.2,.3,2),T)[0],4)
    def test_edge(self):self.assertEqual(self.witness((.5,-2,0),T)[1],(.5,0.,0.))
    def test_vertex(self):self.assertEqual(self.witness((-1,-1,0),T)[1],(0.,0.,0.))
    def test_on_face(self):self.assertEqual(self.witness((.2,.3,0),T)[0],0)
    def test_degenerate_line(self):self.assertEqual(self.witness((.5,1,0),((0,0,0),(1,0,0),(2,0,0)))[0],1)
    def test_degenerate_point(self):self.assertEqual(self.witness((1,0,0),((0,0,0),)*3)[0],1)
    def test_thin_triangle(self):self.assertAlmostEqual(self.witness((.2,1e-8,1),((0,0,0),(1,0,0),(1,1e-7,0)))[0],1)
    def test_orientation(self):self.assertAlmostEqual(m.closest((.3,.4,1),T)[0],m.closest((.3,.4,1),T[::-1])[0])
    def test_translation(self):
        p=(.2,.4,2);shift=(3,-2,7);f=lambda v:tuple(x+y for x,y in zip(v,shift))
        self.assertAlmostEqual(m.closest(p,T)[0],m.closest(f(p),tuple(f(v) for v in T))[0])
    def test_rotation(self):
        f=lambda v:(-v[1],v[2],-v[0]);p=(.2,.4,2)
        self.assertAlmostEqual(m.closest(p,T)[0],m.closest(f(p),tuple(f(v) for v in T))[0])
    def test_scaling(self):
        for scale in (.01,3,100):self.assertAlmostEqual(m.closest((.2*scale,.4*scale,2*scale),tuple(tuple(x*scale for x in v) for v in T))[0],4*scale**2)
    def test_nonfinite(self):
        for p in ((math.nan,0,0),(0,math.inf,0),(0,0,1e9)):
            with self.assertRaises(ValueError):m.closest(p,T)
    def test_bad_mesh(self):
        for v,f in (([],[]),(T,[(0,1,3)]),(T,[(0,1,-1)]),(T,[(0,1,True)])):
            with self.assertRaises(ValueError):m.SurfaceIndex(v,f)
    def test_bad_leaf(self):
        with self.assertRaises(ValueError):m.SurfaceIndex(T,[(0,1,2)],leaf=0)
    def test_single_face(self):self.assertAlmostEqual(m.SurfaceIndex(T,[(0,1,2)]).nearest((.2,.2,3))['distance'],3)
    def test_tie(self):self.assertEqual(m.SurfaceIndex(T,[(0,1,2)]*8,leaf=1).nearest((.2,.2,1))['object_triangle'],0)
    def test_budget(self):
        with self.assertRaisesRegex(ValueError,'distance_node_budget'):m.SurfaceIndex(T,[(0,1,2)]*8,leaf=1).nearest((.2,.2,1),max_nodes=1)
    def test_query_nonfinite(self):
        with self.assertRaises(ValueError):m.SurfaceIndex(T,[(0,1,2)]).nearest((0,0,math.nan))
    def test_accelerated_exhaustive(self):
        rng=random.Random(824);v=[tuple(rng.uniform(-2,2) for _ in range(3)) for _ in range(180)];f=[(i,i+1,i+2) for i in range(0,180,3)]
        for leaf in (1,8,64):
            bvh=m.SurfaceIndex(v,f,leaf)
            for _ in range(25):
                p=tuple(rng.uniform(-3,3) for _ in range(3));brute=min((m.closest(p,t)[0],i) for i,t in enumerate(bvh.tri));got=bvh.nearest(p)
                self.assertAlmostEqual(got['distance']**2,brute[0],12);self.assertEqual(got['object_triangle'],brute[1]);self.witness(p,bvh.tri[got['object_triangle']])
    def test_analytic_grid(self):
        v=[];f=[]
        for x in range(8):
            for y in range(8):
                i=len(v);v.extend([(x,y,0),(x+1,y,0),(x,y+1,0),(x+1,y+1,0)]);f.extend([(i,i+1,i+2),(i+1,i+3,i+2)])
        index=m.SurfaceIndex(v,f)
        for x,y,z in ((.3,.7,2),(4.6,3.2,-.4),(7.99,1.,.05)):self.assertAlmostEqual(index.nearest((x,y,z))['distance'],abs(z),12)
    def test_input_immutable(self):
        v=[list(p) for p in T];f=[[0,1,2]];idx=m.SurfaceIndex(v,f);v[0][2]=99;f[0][0]=2
        self.assertAlmostEqual(idx.nearest((.2,.2,1))['distance'],1)
    def test_normalized_scale_invariant(self):
        rows,s=m.measure(m.SurfaceIndex(T,[(0,1,2)]),[(.2,.2,1)])
        big=tuple(tuple(5*x for x in p) for p in T);rows2,_=m.measure(m.SurfaceIndex(big,[(0,1,2)]),[(1,1,5)])
        self.assertAlmostEqual(rows[0]['normalized_distance'],rows2[0]['normalized_distance'])
    def test_measure_limits(self):
        idx=m.SurfaceIndex(T,[(0,1,2)])
        for vs in ([],[(0,0,0)]*2001):
            with self.assertRaises(ValueError):m.measure(idx,vs)
    def test_zero_extent(self):
        with self.assertRaises(ValueError):m.measure(m.SurfaceIndex([(0,0,0)],[(0,0,0)]),[(0,0,0)])
    def test_statistics(self):
        rows,s=m.measure(m.SurfaceIndex(T,[(0,1,2)]),[(.2,.2,z) for z in (0,1,2)])
        self.assertEqual(s['median'],1);self.assertEqual(s['minimum'],0);self.assertAlmostEqual(s['p90'],1.8);self.assertEqual([r['vertex_index'] for r in rows],[0,1,2])
    def test_purpose_refused(self):
        with self.assertRaisesRegex(ValueError,'purpose_required'):m.build(None,None,None,*([None]*9),purpose='placement')
    def test_verify_purpose_refused(self):
        with self.assertRaisesRegex(ValueError,'purpose_required'):m.verify(None,None,None,None,None,purpose='placement')
    def test_html_escaping(self):
        raw=m.html({'marker':'</script><img src=x>'});self.assertNotIn(b'</script><img',raw);self.assertIn(b'\\u003c/script',raw);self.assertIn(b'connect-src \'none\'',raw)
if __name__=='__main__':unittest.main()
