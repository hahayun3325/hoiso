import copy,importlib.util,json,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('adaptive_pipeline',ROOT/'src/foho/geometry/adaptive_pipeline.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def fixture():
 stage=dict(depth=0,leaf_cells=1,queries_used=0,query_budget=8,threshold=.2,total_area=1.,area_fraction_lower=.1,area_fraction_upper=.5,unresolved_area_fraction=.4,areas={},counts={})
 final={**stage,'depth':1,'leaf_cells':2,'queries_used':4,'area_fraction_lower':.2,'area_fraction_upper':.3,'unresolved_area_fraction':.1}
 common=dict(case_id='case',object_binding={'sha256':'object'},scene_frame='frame',units='unverified',reference_status='awaiting_reference',placement_ready=False,selected_candidate=None,accepted_scale=None)
 p,a,b=[dict(common,candidates=[]) for _ in range(3)]
 for x in [a,b]:x.update(threshold=.2,threshold_object_diagonal_ratio=.02)
 for id in ['primary','minimum_scale','maximum_scale','minimum_scale_refined']:
  c=dict(id=id,hand_binding={'sha256':id},collision_gate='blocked_transverse_crossing' if id=='minimum_scale' else 'clear_surface_separation_only',accepted=False)
  p['candidates'].append(dict(c,conditional_scale=2.,unsigned_surface_gap=.01,vertex_distances={},profiles=[dict(stage,threshold_object_diagonal_ratio=.02)]))
  a['candidates'].append(dict(c,stages=[copy.deepcopy(stage),copy.deepcopy(final)],stop_reason='depth_limit'))
  b['candidates'].append(dict(c,stage=copy.deepcopy(final),leaves=[{},{}],witnesses=[{}],stop_reason='depth_limit'))
 return p,a,b
class Pipeline(unittest.TestCase):
 def setUp(self):self.p,self.a,self.b=fixture()
 def run_join(self):return m.summarize(self.p,self.a,self.b)
 def test_join_preserves_blocked_branch(self):self.assertEqual(self.run_join()[1]['collision_gate'],'blocked_transverse_crossing')
 def test_join_by_id_not_order(self):self.b['candidates'].reverse();self.assertEqual(self.run_join()[0]['id'],'primary')
 def test_missing_candidate_refused(self):self.b['candidates'].pop();self.assertRaisesRegex(ValueError,'candidate_set',self.run_join)
 def test_duplicate_candidate_refused(self):self.b['candidates'][1]=self.b['candidates'][0];self.assertRaisesRegex(ValueError,'duplicate_candidate',self.run_join)
 def test_wrong_hand_refused(self):self.b['candidates'][0]['hand_binding']={};self.assertRaisesRegex(ValueError,'candidate_identity',self.run_join)
 def test_changed_collision_refused(self):self.b['candidates'][1]['collision_gate']='clear';self.assertRaisesRegex(ValueError,'candidate_identity',self.run_join)
 def test_wrong_object_refused(self):self.b['object_binding']={};self.assertRaisesRegex(ValueError,'source_identity',self.run_join)
 def test_wrong_case_refused(self):self.a['case_id']='other';self.assertRaisesRegex(ValueError,'source_identity',self.run_join)
 def test_wrong_frame_refused(self):self.a['scene_frame']='other';self.assertRaisesRegex(ValueError,'source_identity',self.run_join)
 def test_wrong_units_refused(self):self.a['units']='meters';self.assertRaisesRegex(ValueError,'source_identity',self.run_join)
 def test_wrong_threshold_refused(self):self.b['threshold']=.3;self.assertRaisesRegex(ValueError,'threshold_identity',self.run_join)
 def test_wrong_profile_refused(self):self.p['candidates'][0]['profiles'][0]['threshold']=.3;self.assertRaisesRegex(ValueError,'threshold_profile',self.run_join)
 def test_duplicate_profile_refused(self):self.p['candidates'][0]['profiles']*=2;self.assertRaisesRegex(ValueError,'threshold_profile',self.run_join)
 def test_changed_coarse_stage_refused(self):self.a['candidates'][0]['stages'][0]['area_fraction_lower']=.11;self.assertRaisesRegex(ValueError,'coarse_stage',self.run_join)
 def test_changed_map_stage_refused(self):self.b['candidates'][0]['stage']['queries_used']=9;self.assertRaisesRegex(ValueError,'map_stage',self.run_join)
 def test_missing_cells_refused(self):self.b['candidates'][0]['leaves'].pop();self.assertRaisesRegex(ValueError,'map_stage',self.run_join)
 def test_changed_stop_refused(self):self.b['candidates'][0]['stop_reason']='resolved';self.assertRaisesRegex(ValueError,'stop_reason',self.run_join)
 def test_acceptance_escalation_refused(self):self.p['placement_ready']=True;self.assertRaisesRegex(ValueError,'source_acceptance',self.run_join)
 def test_candidate_acceptance_refused(self):self.b['candidates'][0]['accepted']=True;self.assertRaisesRegex(ValueError,'candidate_accepted',self.run_join)
 def test_scale_acceptance_refused(self):self.a['accepted_scale']=2.;self.assertRaisesRegex(ValueError,'source_acceptance',self.run_join)
 def test_zero_uncertainty_has_no_percentage(self):
  for x in [self.p['candidates'][0]['profiles'][0],*self.a['candidates'][0]['stages'],self.b['candidates'][0]['stage']]:x['unresolved_area_fraction']=0.
  self.assertIsNone(self.run_join()[0]['unresolved_fraction_reduction'])
 def test_reduction_is_relative_to_initial(self):self.assertAlmostEqual(self.run_join()[0]['unresolved_fraction_reduction'],.75)
 def test_does_not_modify_sources(self):before=copy.deepcopy([self.p,self.a,self.b]);self.run_join();self.assertEqual(before,[self.p,self.a,self.b])
 def test_placement_refused_before_io(self):self.assertRaisesRegex(ValueError,'purpose_required',m.build,*([None]*11),purpose='placement')
 def test_verification_placement_refused(self):self.assertRaisesRegex(ValueError,'purpose_required',m.verify,None,None,purpose='placement')
 def test_markup_escaped(self):
  raw=m.html({'case_id':'</script><img src=x>'},b'rgb');self.assertNotIn(b'</script><img',raw);self.assertIn(b'\\u003c/script',raw)
 def test_complete_local_links(self):
  import re
  links=set(re.findall(r'href="([^"]+)"',m.TEMPLATE));self.assertTrue(links<=m.FILES);self.assertIn('surface_map.html',links)
 def test_widening_refused(self):
  for x in [self.a['candidates'][0]['stages'][-1],self.b['candidates'][0]['stage']]:x['unresolved_area_fraction']=.6
  self.assertRaisesRegex(ValueError,'uncertainty_increased',self.run_join)
if __name__=='__main__':unittest.main()
