import math,unittest
import scene_review as r
K=[[1,0,0],[0,1,0],[0,0,1]]
V=[(0,0,-1),(4,0,-1),(0,-4,-1)];F=[(0,1,2)]
class ReviewTests(unittest.TestCase):
    def test_camera_axes_and_integer_centers(self):
        z,_=r.surface_depth(V,F,K,(5,5));self.assertEqual(z[1*5+1],1);self.assertEqual(z[4],1);self.assertTrue(math.isinf(z[24]))
    def test_perspective_correct_depth(self):
        # Projected triangle (0,0),(4,0),(0,4), vertex depths 1,2,4.
        z,_=r.surface_depth([(0,0,-1),(8,0,-2),(0,-16,-4)],F,K,(5,5))
        self.assertAlmostEqual(z[6],1/(.5/1+.25/2+.25/4))
    def test_nearest_surface_wins(self):
        v=V+[(x*2,y*2,z*2) for x,y,z in V];z,_=r.surface_depth(v,[(3,4,5),(0,1,2)],K,(5,5));self.assertEqual(z[6],1)
    def test_two_sided(self):
        a,_=r.surface_depth(V,F,K,(5,5));b,_=r.surface_depth(V,[(2,1,0)],K,(5,5));self.assertEqual(a,b)
    def test_behind_camera_rejected(self):
        with self.assertRaisesRegex(ValueError,'camera_plane'):r.surface_depth([(0,0,1),*V[1:]],F,K)
    def test_straddling_near_plane_rejected(self):
        with self.assertRaisesRegex(ValueError,'camera_plane'):r.surface_depth([(0,0,0),*V[1:]],F,K)
    def test_degenerate_triangle_has_no_pixels(self):
        z,s=r.surface_depth(V,[(0,0,0)],K,(5,5));self.assertTrue(all(math.isinf(x) for x in z));self.assertEqual(s['projected_degenerate'],1)
    def test_face_index_rejected(self):
        with self.assertRaisesRegex(ValueError,'raster_face'):r.surface_depth(V,[(0,1,3)],K)
    def test_nonfinite_vertex_rejected(self):
        with self.assertRaisesRegex(ValueError,'camera_plane'):r.surface_depth([(math.nan,0,-1),*V[1:]],F,K)
    def test_invalid_camera_rejected(self):
        with self.assertRaisesRegex(ValueError,'raster_K'):r.surface_depth(V,F,[[1,0,0],[0,1,0],[1,0,1]])
    def test_raster_work_budget_enforced(self):
        with self.assertRaisesRegex(ValueError,'work_bound'):r.surface_depth(V,F,K,(5,5),work_limit=3)
    def test_image_bounds_clip(self):
        z,_=r.surface_depth([(-50,50,-1),(50,50,-1),(-50,-50,-1)],F,K,(5,5));self.assertEqual(len(z),25)
    def test_uniform_scene_scaling_keeps_projection(self):
        a,_=r.surface_depth(V,F,K,(5,5));b,_=r.surface_depth([(x*3,y*3,z*3) for x,y,z in V],F,K,(5,5))
        self.assertEqual([math.isfinite(x) for x in a],[math.isfinite(x) for x in b]);self.assertAlmostEqual(b[6]/a[6],3)
    def test_depth_order_partition(self):
        p=r.partition([1,3,2,1,math.inf],[2,2,2,math.inf,1],.01)
        self.assertEqual({k:sum(v) for k,v in p.items()},dict(hand=4,object=4,overlap=3,hand_front=1,object_front=1,near=1,visible_hand=3))
    def test_tolerance_boundary(self):
        p=r.partition([1,1],[1.125,1.25],.125);self.assertEqual(list(p['near']),[1,0]);self.assertEqual(list(p['hand_front']),[0,1])
    def test_invalid_depth_rejected(self):
        for x in [math.nan,-math.inf,-1,0]:
            with self.assertRaisesRegex(ValueError,'depth_values'):r.partition([x],[1],.1)
    def test_iou_and_empty_masks(self):
        s=r.scores([1,1,0],[1,0,1]);self.assertAlmostEqual(s['iou'],1/3);self.assertEqual(s['mask_coverage'],.5)
        self.assertEqual(r.scores([0],[0])['iou'],0);self.assertFalse(s['accuracy_verified'])
    def test_rgb_roundtrip(self):
        b=bytes([10,120,200])*(512*512);self.assertEqual(r.decode_png(r.rgb_png(b)),(3,b))
    def test_png_crc_rejected(self):
        b=r.rgb_png(bytes(512*512*3));b=b[:-1]+bytes([b[-1]^1])
        with self.assertRaisesRegex(ValueError,'PNG_crc'):r.decode_png(b)
    def test_nonbinary_mask_rejected(self):
        with self.assertRaisesRegex(ValueError,'binary_mask'):r.decode_pgm(r.HEADER+bytes([127])*r.SIZE)
    def test_comparison_categories(self):
        layers=r.comparison_layers([1,1,0],[1,0,1]);self.assertEqual([list(x[0]) for x in layers],[[1,0,0],[0,0,1],[0,1,0]])
    def test_html_is_offline_and_does_not_inject_case_text(self):
        out=r.review_html(dict(case_id='</script><b>not executable',candidates=[]),{})
        self.assertNotIn(b'</script><b>not executable',out);self.assertIn(b"connect-src 'none'",out);self.assertIn(b'no accepted placement',out)
if __name__=='__main__':unittest.main()
