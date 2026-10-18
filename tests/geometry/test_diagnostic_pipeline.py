import copy,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).resolve().parents[2]
def load(n):
    spec=importlib.util.spec_from_file_location(n,root/'src/foho/geometry'/(n+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('diagnostic_pipeline');reader=load('scene_candidates')
def stages():
    pin=dict(bytes=7,sha256='a'*64)
    scene=dict(case_id='case',package_binding=pin,placement_ready=False)
    mask=dict(case_id='case',source_package_binding=pin,status='awaiting_reference',metrics=None,reference_binding=None,human_review_record_complete=True,placement_ready=False)
    comp=dict(case_id='case',source_package_binding=pin,reference_status='awaiting_reference',reference_metrics=None,human_review_record_complete=True,placement_ready=False,selected_candidate=None,accepted_scale=None,validation_receipt_binding=pin,profiles={},candidates=[])
    return scene,mask,comp
class PipelineTests(unittest.TestCase):
    def test_missing_reference_does_not_block_diagnostic_interface(self):
        r=m.summarize(*stages());self.assertTrue(r['candidate_loading_available']);self.assertEqual(r['reference_status'],'awaiting_reference');self.assertIsNone(r['reference_metrics'])
    def test_reference_scores_do_not_grant_accuracy_or_placement(self):
        s,v,c=stages();v.update(status='reference_scored',metrics=dict(iou=1),reference_binding=dict(bytes=1,sha256='b'*64));c.update(reference_status=v['status'],reference_metrics=v['metrics']);r=m.summarize(s,v,c)
        self.assertEqual(r['reference_metrics']['iou'],1)
        for k in ['mask_accuracy_verified','reference_provenance_verified','scale_identified','placement_ready','full_parent_acceptance','physical_contact_verified']:self.assertFalse(r[k])
    def test_case_mismatch(self):
        s,v,c=stages();c['case_id']='other'
        with self.assertRaisesRegex(ValueError,'case_mismatch'):m.summarize(s,v,c)
    def test_source_mismatch(self):
        s,v,c=stages();c['source_package_binding']={}
        with self.assertRaisesRegex(ValueError,'source_mismatch'):m.summarize(s,v,c)
    def test_reference_state_mismatch(self):
        s,v,c=stages();c['reference_status']='reference_scored'
        with self.assertRaisesRegex(ValueError,'reference_state'):m.summarize(s,v,c)
    def test_reference_metrics_mismatch(self):
        s,v,c=stages();c['reference_metrics']={}
        with self.assertRaisesRegex(ValueError,'reference_metrics'):m.summarize(s,v,c)
    def test_pending_with_reference_rejected(self):
        s,v,c=stages();v['reference_binding']={}
        with self.assertRaisesRegex(ValueError,'reference_presence'):m.summarize(s,v,c)
    def test_scored_without_reference_rejected(self):
        s,v,c=stages();v.update(status='reference_scored',metrics={});c.update(reference_status='reference_scored',reference_metrics={})
        with self.assertRaisesRegex(ValueError,'reference_presence'):m.summarize(s,v,c)
    def test_missing_review_rejected(self):
        s,v,c=stages();v['human_review_record_complete']=False
        with self.assertRaisesRegex(ValueError,'human_review'):m.summarize(s,v,c)
    def test_selection_not_propagated(self):
        s,v,c=stages();c['selected_candidate']='primary'
        with self.assertRaisesRegex(ValueError,'selection_refused'):m.summarize(s,v,c)
    def test_scale_not_propagated(self):
        s,v,c=stages();c['accepted_scale']=2
        with self.assertRaisesRegex(ValueError,'selection_refused'):m.summarize(s,v,c)
    def test_placement_not_propagated(self):
        s,v,c=stages();s['placement_ready']=True
        with self.assertRaisesRegex(ValueError,'placement_refused'):m.summarize(s,v,c)
    def test_source_stages_not_modified(self):
        a=stages();b=copy.deepcopy(a);m.summarize(*a);self.assertEqual(a,b)
    def test_build_placement_refused_before_reads(self):
        with self.assertRaisesRegex(ValueError,'purpose_required'):m.build(*([None]*11),purpose='placement')
    def test_verify_placement_refused_before_reads(self):
        with self.assertRaisesRegex(ValueError,'purpose_required'):m.verify(*([None]*11),purpose='placement')
    def test_load_placement_refused_before_reads(self):
        with self.assertRaisesRegex(ValueError,'purpose_required'):m.load_candidate(*([None]*11),candidate_id='primary',purpose='placement')
    def test_load_requires_explicit_candidate(self):
        for candidate in [None,'auto','best','']:
            with self.subTest(candidate=candidate),self.assertRaisesRegex(ValueError,'explicit_candidate'):m.load_candidate(None,None,None,reader,*([None]*7),candidate_id=candidate,purpose=m.PURPOSE)
    def test_inventory_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t).resolve();(p/'x').write_bytes(b'original\x00');self.assertEqual(m.inventory(p,reader),{'x':b'original\x00'})
    def test_inventory_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t).resolve();(p/'x').write_bytes(b'keep');(p/'alias').symlink_to(p/'x')
            with self.assertRaisesRegex(ValueError,'symlink'):m.inventory(p,reader)
    def test_inventory_bound(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t).resolve()
            for i in range(m.MAX_FILES+1):(p/str(i)).write_bytes(b'')
            with self.assertRaisesRegex(ValueError,'file_count'):m.inventory(p,reader)
    def test_html_script_escape(self):
        r=m.summarize(*stages());r['case_id']='</script><script>alert(1)</script>';b=m.html(r);self.assertNotIn(b'alert(1)</script>',b);self.assertIn(b'\\u003c/script',b)
    def test_workspace_receipt_mismatch_stops_before_rebuild(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t).resolve();(p/'workspace.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,'receipt_changed'):m.verify(p,'0'*64,'case',reader,*([None]*7),purpose=m.PURPOSE)
if __name__=='__main__':unittest.main(verbosity=2)
