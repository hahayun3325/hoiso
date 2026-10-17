import importlib.util,math,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('domain',ROOT/'src/foho/geometry/hand_domain_audit.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
# Open rectangular ring and a hand-facing tip, with five vertices.
V=[[-1,-2,-10],[-1,2,-10],[0,2,-11],[0,-2,-11],[20,0,-10]]
F=[(0,1,4),(1,2,4),(2,3,4),(3,0,4)]
K=[[10,0,8],[0,10,8],[0,0,1]]

class DomainTests(unittest.TestCase):
    def test_single_open_loop(self):self.assertEqual(d.boundary_loop(V,F),[0,1,2,3])
    def test_winding_does_not_change_boundary(self):self.assertEqual(d.boundary_loop(V,[tuple(reversed(f)) for f in F]),[0,1,2,3])
    def test_closed_mesh_refused(self):
        with self.assertRaisesRegex(ValueError,'open_boundary'):d.boundary_loop(V,F+[(0,2,1),(0,3,2)])
    def test_two_boundaries_refused(self):
        with self.assertRaisesRegex(ValueError,'multiple_boundary'):d.boundary_loop(V+V,F+[tuple(i+5 for i in f) for f in F])
    def test_nonmanifold_refused(self):
        with self.assertRaisesRegex(ValueError,'nonmanifold'):d.boundary_loop(V,F+[(0,1,2),(0,1,3)])
    def test_duplicate_face_refused(self):
        with self.assertRaisesRegex(ValueError,'duplicate_face'):d.boundary_loop(V,F+[F[0]])
    def test_invalid_index_refused(self):
        with self.assertRaisesRegex(ValueError,'triangle'):d.boundary_loop(V,[(0,1,99)])
    def test_camera_axes(self):self.assertEqual(d.project([[1,2,-10]],K),[(9.,6.)])
    def test_camera_plane_refused(self):
        with self.assertRaisesRegex(ValueError,'camera_plane'):d.project([[1,2,0]],K)
    def test_nonfinite_vertex_refused(self):
        with self.assertRaisesRegex(ValueError,'camera_plane'):d.project([[1,float('nan'),-10]],K)
    def test_partition_covers_every_pixel_once(self):
        r,b=d.partition_domain(V,F,K,16,16,0)
        self.assertTrue(all(sum(x[i] for x in r.values())==1 for i in range(256)))
        self.assertEqual(r['hand_side'][8*16+14],1);self.assertEqual(r['beyond_boundary'][8*16+1],1)
        self.assertGreater(b['hand_facing_unit_normal'][0],.99)
    def test_boundary_inside_band(self):
        r,b=d.partition_domain(V,F,K,16,16,2)
        for point in b['boundary_uv']:
            value=sum((point[j]-b['center_uv'][j])*b['hand_facing_unit_normal'][j] for j in (0,1))
            self.assertLessEqual(b['signed_band_limits_px'][0],value);self.assertLessEqual(value,b['signed_band_limits_px'][1])
    def test_uniform_scale_preserves_partition(self):
        a,_=d.partition_domain(V,F,K,16,16,0);b,_=d.partition_domain([[x*2.5 for x in v] for v in V],F,K,16,16,0)
        self.assertEqual(a,b)
    def test_isotropic_boundary_refused(self):
        square=[[-2,-2,-10],[-2,2,-10],[2,2,-10],[2,-2,-10],[6,0,-10]]
        with self.assertRaisesRegex(ValueError,'projection_ambiguous'):d.partition_domain(square,F,K,16,16)
    def test_oversized_image_refused(self):
        with self.assertRaisesRegex(ValueError,'image_shape'):d.partition_domain(V,F,K,513,512)
    def test_bad_margin_refused(self):
        with self.assertRaisesRegex(ValueError,'margin'):d.partition_domain(V,F,K,16,16,-1)
    def test_diagonal_components_and_bbox(self):
        rows=d.components([1,0,0,0,1,0,0,0,1],3,3)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['pixels'],3);self.assertEqual(rows[0]['bbox_xyxy_inclusive'],[0,0,2,2]);self.assertTrue(rows[0]['touches_image_edge'])
    def test_component_order_and_interior(self):
        a=[0]*25;a[6]=a[24]=1;rows=d.components(a,5,5)
        self.assertEqual([r['first_pixel'] for r in rows],[6,24]);self.assertFalse(rows[0]['touches_image_edge'])
    def test_empty_components(self):self.assertEqual(d.components([0]*4,2,2),[])
    def test_region_count_conservation_and_empty_iou(self):
        regions={'hand_side':[1,1,0,0],'boundary_band':[0,0,1,0],'beyond_boundary':[0,0,0,1]}
        rows=d.count_regions([1,1,0,0],[1,0,0,1],regions)
        self.assertEqual(rows['hand_side']['iou'],.5);self.assertIsNone(rows['boundary_band']['iou'])
        self.assertEqual(sum(r['mask_pixels'] for r in rows.values()),2);self.assertEqual(rows['beyond_boundary']['mask_only'],1)
    def test_overlapping_regions_refused(self):
        with self.assertRaisesRegex(ValueError,'region_partition'):d.count_regions([1],[1],{k:[1] for k in ['hand_side','boundary_band','beyond_boundary']})

if __name__=='__main__':unittest.main(verbosity=2)
