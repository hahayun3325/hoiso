import copy,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
def load(name,path=None):
 s=importlib.util.spec_from_file_location(name,path or ROOT/'src/foho/geometry'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=load('scene_readiness');records=load('mask_review_record');sc=load('scene_candidates')
class ReadinessTests(unittest.TestCase):
 def setUp(self):
  self.ctx={'case_id':'fixture','manifest_binding':{'bytes':1,'sha256':'a'*64}}
  self.m=dict(schema='tracehoi.DiagnosticSceneBundle.v1',case_id='fixture',placement_ready=False,full_parent_acceptance=False,scale_identified=False,physical_contact_verified=False,selected_candidate=None,accepted_scale=None,mask_review_required=True,candidates=[])
  for id in records.IDS:
   crossing=id=='minimum_scale';self.m['candidates'].append(dict(id=id,accepted=False,pipeline_admissible=False,conditional_scale=2.2,unsigned_surface_gap=0 if crossing else .1,collision_gate='blocked_transverse_crossing' if crossing else 'clear_surface_separation_only',blockers=sc.BLOCKERS+(['transverse_mesh_crossing'] if crossing else [])))
 def assess(self,raw=None):return r.assess(self.m,self.ctx,records,raw)
 def reviewed(self,decision='needs_revision'):
  row=records.blank(copy.deepcopy(self.ctx));row.update(state='reviewed',reviewer='Test fixture',reviewed_at='2026-10-17T19:00:00Z',original_image_inspected=True,provisional_mask_inspected=True,decision=decision,notes='Test only',findings=[dict(kind='mask_excess',candidate='mask_only',bbox_xyxy_inclusive=[1,2,3,4],note='Test only')]);return row
 def test_missing_record_explicit_pending(self):
  out=self.assess();self.assertEqual(out['review']['state'],'missing');self.assertIsNone(out['review']['input_binding']);self.assertEqual(out['next_action'],'complete_mask_review')
 def test_draft_does_not_enable_planning(self):
  out=self.assess(records.encode(records.blank(copy.deepcopy(self.ctx))));self.assertEqual(out['review']['state'],'draft');self.assertFalse(out['stages'][1]['available'])
 def test_complete_revision_record_enables_only_planning(self):
  out=self.assess(records.encode(self.reviewed()));self.assertTrue(out['stages'][1]['available']);self.assertFalse(out['stages'][2]['available']);self.assertEqual(out['next_action'],'plan_mask_revision')
 def test_uncertain_routes_to_uncertainty_resolution(self):self.assertEqual(self.assess(records.encode(self.reviewed('uncertain')))['next_action'],'review_reported_uncertainty')
 def test_visually_consistent_does_not_clear_accuracy(self):
  out=self.assess(records.encode(self.reviewed('visually_consistent')));self.assertFalse(out['mask_accuracy_verified']);self.assertTrue(out['mask_review_required']);self.assertEqual(out['next_action'],'design_independent_mask_validation')
 def test_each_decision_preserves_all_scientific_gates(self):
  for d in ['needs_revision','uncertain','visually_consistent']:
   out=self.assess(records.encode(self.reviewed(d)))
   for k in ['mask_accuracy_verified','scale_identified','physical_contact_verified','geometric_accuracy_verified','placement_ready','full_parent_acceptance']:self.assertIs(out[k],False)
 def test_crossing_branch_remains_diagnostic_and_blocked(self):
  c=self.assess()['candidates'][1];self.assertTrue(c['diagnostic_available']);self.assertFalse(c['placement_available']);self.assertIn('transverse_mesh_crossing',c['blockers'])
 def test_clear_gap_does_not_approve_contact(self):self.assertFalse(self.assess()['physical_contact_verified'])
 def test_bad_record_not_silently_treated_as_missing(self):
  with self.assertRaises(ValueError):self.assess(b'{}')
 def test_wrong_record_context(self):
  x=self.reviewed();x['context']['case_id']='other'
  with self.assertRaisesRegex(ValueError,'context_binding'):self.assess(records.encode(x))
 def test_input_bytes_binding_preserved(self):
  raw=json.dumps(self.reviewed(),separators=(',',':')).encode();self.assertEqual(self.assess(raw)['review']['input_binding'],records.binding(raw))
 def test_source_not_mutated(self):
  before=copy.deepcopy(self.m);self.assess(records.encode(self.reviewed()));self.assertEqual(before,self.m)
 def test_record_cannot_select_scale(self):
  x=self.reviewed();x['accepted_scale']=2.2
  with self.assertRaisesRegex(ValueError,'forbidden_selection'):self.assess(records.encode(x))
 def test_wrong_case_or_schema(self):
  for key in ['case_id','schema']:
   m=copy.deepcopy(self.m);m[key]='other'
   with self.assertRaisesRegex(ValueError,'readiness_identity'):r.assess(m,self.ctx,records)
 def test_candidate_admission_refused(self):
  self.m['candidates'][0]['accepted']=True
  with self.assertRaisesRegex(ValueError,'readiness_candidate_admission'):self.assess()
 def test_missing_collision_blocker_refused(self):
  self.m['candidates'][1]['blockers']=sc.BLOCKERS
  with self.assertRaisesRegex(ValueError,'readiness_blockers'):self.assess()
 def test_unknown_collision_gate_refused(self):
  self.m['candidates'][0]['collision_gate']='certified'
  with self.assertRaisesRegex(ValueError,'readiness_collision_gate'):self.assess()
 def test_missing_candidate_refused(self):
  self.m['candidates'].pop()
  with self.assertRaisesRegex(ValueError,'readiness_candidates'):self.assess()
 def test_prepare_placement_always_refused(self):
  with patch.object(r,'evaluate',return_value=self.assess()):
   with self.assertRaisesRegex(ValueError,'stage_blocked:placement'):r.prepare_stage(None,None,None,None,None,sc,None,None,records,'placement')
 def test_unknown_stage_refused(self):
  with self.assertRaisesRegex(ValueError,'unknown_stage'):r.prepare_stage(None,None,None,None,None,sc,None,None,records,'run_gpu')
 def test_revision_handoff_preserves_exact_regions_and_notes(self):
  row=self.reviewed();raw=records.encode(row)
  with patch.object(r,'evaluate',return_value=self.assess(raw)):
   out=r.prepare_stage(None,None,'fixture',None,None,sc,None,None,records,'mask_revision_planning',record_raw=raw)
  self.assertEqual(out['findings'],row['findings']);self.assertEqual(out['notes'],row['notes']);self.assertTrue(out['planning_only']);self.assertFalse(out['mask_modified'])
 def test_revision_cannot_select_candidate(self):
  raw=records.encode(self.reviewed())
  with patch.object(r,'evaluate',return_value=self.assess(raw)):
   with self.assertRaisesRegex(ValueError,'revision_has_no_selected_candidate'):r.prepare_stage(None,None,None,None,None,sc,None,None,records,'mask_revision_planning',candidate='primary',record_raw=raw)
 def test_diagnostic_requires_explicit_candidate(self):
  with patch.object(r,'evaluate',return_value=self.assess()):
   with self.assertRaisesRegex(ValueError,'explicit_candidate_required'):r.prepare_stage(None,None,None,None,None,sc,None,None,records,'diagnostic_export')
 def test_diagnostic_uses_reader_with_diagnostic_purpose(self):
  with patch.object(r,'evaluate',return_value=self.assess()),patch.object(sc,'load_candidate',return_value={'accepted':False,'hand_mesh_bytes':b'a'}) as loader:
   out=r.prepare_stage('scene','hash','fixture','review','sha',sc,None,None,records,'diagnostic_export',candidate='primary')
   self.assertEqual(loader.call_args.kwargs['purpose'],'diagnostic');self.assertEqual(out['scene']['hand_mesh_bytes'],b'a')
 def test_dashboard_escapes_embedded_data_and_has_no_network(self):
  out=self.assess();out['case_id']='</script><script>bad()</script>';html=r.html(out);self.assertNotIn(out['case_id'].encode(),html);self.assertIn(b"connect-src 'none'",html);self.assertIn(b'TRACEHOI_MASK_REVIEW_RECORD_Z2x7Pf4Z.html',html)
 def test_missing_review_and_draft_have_different_provenance(self):
  a=self.assess();b=self.assess(records.encode(records.blank(copy.deepcopy(self.ctx))));self.assertIsNone(a['review']['validation']);self.assertIsNotNone(b['review']['validation']);self.assertNotEqual(a['review']['input_binding'],b['review']['input_binding'])
if __name__=='__main__':unittest.main()
