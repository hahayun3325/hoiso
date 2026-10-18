import copy,importlib.util,math,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('candidate_comparison',Path(__file__).resolve().parents[2]/'src/foho/geometry/candidate_comparison.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def row(i,x=2,y=.5,z=.1,gate='clear_surface_separation_only'):return dict(id=i,joint_median_px=x,visible_mask_iou=y,surface_gap=z,collision_gate=gate)
class ComparisonTests(unittest.TestCase):
    def test_dominance(self):
        r=m.compare([row('a',1,.7),row('b',2,.6)],'image_agreement');self.assertEqual(r['nondominated_ids'],['a']);self.assertEqual(r['relations'],[dict(better_on_profile='a',dominated_on_profile='b')])
    def test_tradeoff(self):self.assertEqual(m.compare([row('a',1,.5),row('b',2,.7)],'image_agreement')['nondominated_ids'],['a','b'])
    def test_ties_preserved(self):self.assertEqual(m.compare([row('a'),row('b')],'image_agreement')['nondominated_ids'],['a','b'])
    def test_proximity_changes_frontier(self):
        r=[row('a',1,.7,.1),row('b',2,.5,.01)];self.assertEqual(m.compare(r,'image_agreement')['nondominated_ids'],['a']);self.assertEqual(m.compare(r,'image_and_proximity_hypothesis')['nondominated_ids'],['a','b'])
    def test_crossing_cannot_dominate(self):
        r=m.compare([row('a',1,1,0,'blocked_transverse_crossing'),row('b')],'image_agreement');self.assertEqual(r['nondominated_ids'],['b']);self.assertEqual(r['crossing_blocked_ids'],['a'])
    def test_all_crossing_empty_frontier(self):self.assertEqual(m.compare([row('a',gate='blocked_transverse_crossing')],'image_agreement')['nondominated_ids'],[])
    def test_duplicate_id(self):
        with self.assertRaisesRegex(ValueError,'unique'):m.compare([row('a'),row('a')],'image_agreement')
    def test_unknown_gate(self):
        with self.assertRaisesRegex(ValueError,'unknown_collision'):m.compare([row('a',gate='safe')],'image_agreement')
    def test_unknown_profile(self):
        with self.assertRaisesRegex(ValueError,'unknown_comparison'):m.compare([row('a')],'placement')
    def test_nonfinite(self):
        for v in [float('nan'),float('inf'),-1,True,'2']:
            with self.subTest(v=v),self.assertRaises(ValueError):m.compare([row('a',x=v)],'image_agreement')
    def test_bad_iou(self):
        with self.assertRaises(ValueError):m.compare([row('a',y=1.001)],'image_agreement')
    def test_unused_gap_still_validated(self):
        with self.assertRaises(ValueError):m.compare([row('a',z=None)],'image_agreement')
    def test_quantization_suppresses_float_noise(self):self.assertEqual(m.compare([row('a',7.238483416371371),row('b',7.238483416371418)],'image_agreement')['nondominated_ids'],['a','b'])
    def test_round_half_even(self):self.assertEqual(m.key(1.0000005,'joint_median_px'),1000000);self.assertEqual(m.key(1.0000015,'joint_median_px'),1000002)
    def test_no_mutation_or_selection(self):
        a=[row('a'),row('b')];b=copy.deepcopy(a);r=m.compare(a,'image_agreement');self.assertEqual(a,b);self.assertIsNone(r['selected_candidate']);self.assertFalse(r['placement_ready']);self.assertFalse(r['candidates_removed'])
    def test_order_independent_relations(self):
        a=[row('a',1,.8),row('b',2,.6),row('c',3,.7)];r=m.compare(a,'image_agreement');s=m.compare(a[::-1],'image_agreement');self.assertEqual(r['nondominated_ids'],s['nondominated_ids']);self.assertEqual({tuple(x.items()) for x in r['relations']},{tuple(x.items()) for x in s['relations']})
    def test_empty(self):
        with self.assertRaises(ValueError):m.compare([],'image_agreement')
    def test_bound(self):
        with self.assertRaises(ValueError):m.compare([row(str(i)) for i in range(33)],'image_agreement')
    def test_injection_escaped(self):
        raw=m.html(dict(case_id='</script><script>alert(1)</script>'),b'');self.assertNotIn(b'alert(1)</script>',raw);self.assertIn(b'\\u003c/script',raw)
    def test_placement_refused_early(self):
        with self.assertRaisesRegex(ValueError,'purpose_required'):m.build(*([None]*12),purpose='placement')
if __name__=='__main__':unittest.main(verbosity=2)
