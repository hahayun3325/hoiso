"""Synthetic review records only; never represents a user's observations."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import scene_candidates as sc,scene_review as renderer,mask_review_record as records,scene_readiness as ready,diagnostic_scene_export as exporter,review_intake as intake
import test_scene_readiness as readiness_fixture

class SourceFixture:
    def __init__(self,root,m):self.root=root;self.m=m;self.embedded=None
    def verify(self,root,digest,case,*mods,purpose):
        sc.require(sc.binding((Path(root)/'package.json').read_bytes())['sha256']==digest,'fixture_source_digest')
        sc.require((self.root/'unchanged').read_bytes()==b'original source','fixture_source_changed')
        return dict(package_binding=sc.binding((self.root/'package.json').read_bytes()))

class ReaderFixture:
    def __init__(self,m):self.m=m
    def __getattr__(self,n):return getattr(sc,n)
    def inspect_bundle(self,*args):return self.m,dict(original_rgb=renderer.rgb_png(bytes([50,60,70])*(512*512)),hand_mask=renderer.pgm(bytes([255])+bytes(512*512-1)))

class ReadyFixture:
    def __init__(self,m,ctx):self.m=m;self.ctx=ctx
    def evaluate(self,*args):return ready.assess(self.m,self.ctx,records,args[-1])
    def prepare_stage(self,*args,**kw):
        with patch.object(ready,'evaluate',return_value=ready.assess(self.m,self.ctx,records,kw['record_raw'])):
            return ready.prepare_stage(*args,**kw)

class IntakeTests(unittest.TestCase):
    def setUp(self):
        f=readiness_fixture.ReadinessTests();f.setUp();self.m=f.m;self.ctx=f.ctx;self.reviewed=f.reviewed
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.source=self.root/'source';self.source.mkdir()
        self.package=dict(source_manifest_binding=dict(bytes=1,sha256='a'*64),source_review_binding=dict(bytes=1,sha256='b'*64),review_input_binding=None)
        self.write_package();(self.source/'unchanged').write_bytes(b'original source');(self.source/intake.FORM).write_bytes(b'fixture form')
        self.reader=ReaderFixture(self.m);self.ready=ReadyFixture(self.m,self.ctx);self.export=SourceFixture(self.source,self.m)
        self.mods=(self.reader,renderer,None,records,self.ready,self.export)
    def tearDown(self):self.tmp.cleanup()
    def write_package(self):
        raw=sc.encode(self.package);(self.source/'package.json').write_bytes(raw);self.sha=sc.binding(raw)['sha256']
    def build(self,raw=None,purpose='review_intake'):return intake.build(self.source,self.sha,'fixture',*self.mods,record_raw=raw,purpose=purpose)
    def publish(self,raw=None):
        report,files=self.build(raw);out=self.root/'result';exporter.publish(out,files,sc);return report,files,out
    def verify(self,out,sha=None,purpose='review_intake'):
        return intake.verify(out,sha or sc.binding((out/'files.json').read_bytes())['sha256'],self.source,self.sha,'fixture',*self.mods,purpose=purpose)
    def test_missing_review_has_no_human_findings(self):
        r,f=self.build();self.assertEqual(r['status'],'pending_human_review');self.assertFalse(r['human_review_record_complete']);self.assertNotIn('review_original.json',f);self.assertNotIn('revision_plan.json',f)
    def test_complete_revision_handoff_keeps_regions_and_bytes(self):
        record=self.reviewed();raw=json.dumps(record,separators=(',',':')).encode();r,f=self.build(raw)
        self.assertEqual(f['review_original.json'],raw);p=sc.parse(f['revision_plan.json']);self.assertEqual(p['findings'],record['findings']);self.assertEqual(p['notes'],record['notes']);self.assertTrue(r['revision_plan_available'])
    def test_uncertain_does_not_create_revision(self):
        r,f=self.build(records.encode(self.reviewed('uncertain')));self.assertEqual(r['next_action'],'review_reported_uncertainty');self.assertNotIn('revision_plan.json',f)
    def test_consistent_is_not_accuracy_approval(self):
        r,_=self.build(records.encode(self.reviewed('visually_consistent')));self.assertFalse(r['mask_accuracy_verified']);self.assertFalse(r['placement_ready']);self.assertEqual(r['next_action'],'design_independent_mask_validation')
    def test_draft_refused(self):
        with self.assertRaisesRegex(ValueError,'completed_human_record'):self.build(records.encode(records.blank(self.ctx)))
    def test_wrong_evidence_refused(self):
        r=self.reviewed();r['context']['case_id']='wrong'
        with self.assertRaisesRegex(ValueError,'context_binding'):self.build(records.encode(r))
    def test_duplicate_json_refused(self):
        with self.assertRaisesRegex(ValueError,'duplicate_key'):self.build(b'{"state":"draft","state":"reviewed"}')
    def test_forbidden_acceptance_refused(self):
        r=self.reviewed();r['placement_ready']=True
        with self.assertRaisesRegex(ValueError,'forbidden_admission'):self.build(records.encode(r))
    def test_inherited_record_is_not_dropped(self):
        raw=records.encode(self.reviewed());(self.source/'human_review.json').write_bytes(raw);self.package['review_input_binding']=records.binding(raw);self.write_package()
        r,f,out=self.publish();self.assertEqual(r['record_source'],'embedded_package');self.assertEqual(f['review_original.json'],raw);self.assertTrue(self.verify(out)['verified'])
    def test_explicit_record_is_a_new_snapshot(self):
        old=records.encode(self.reviewed());(self.source/'human_review.json').write_bytes(old);self.package['review_input_binding']=records.binding(old);self.write_package()
        raw=records.encode(self.reviewed('uncertain'));r,f=self.build(raw);self.assertEqual(r['record_source'],'explicit_record');self.assertEqual((self.source/'human_review.json').read_bytes(),old)
    def test_missing_roundtrip_and_relocation(self):
        r,f,out=self.publish();dest=self.root/'moved';out.rename(dest);self.assertTrue(self.verify(dest)['verified'])
    def test_completed_roundtrip(self):
        r,f,out=self.publish(records.encode(self.reviewed()));self.assertTrue(self.verify(out)['revision_plan_available'])
    def test_changed_record_refused(self):
        r,f,out=self.publish(records.encode(self.reviewed()));(out/'review_original.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'intake_file_binding'):self.verify(out)
    def test_forged_plan_refused_after_rehash(self):
        r,f,out=self.publish(records.encode(self.reviewed()));p=sc.parse(f['revision_plan.json']);p['findings']=[];raw=sc.encode(p);(out/'revision_plan.json').write_bytes(raw)
        receipt=sc.parse(f['files.json']);receipt['files']['revision_plan.json']=sc.binding(raw);(out/'files.json').write_bytes(sc.encode(receipt))
        with self.assertRaisesRegex(ValueError,'intake_semantic'):self.verify(out)
    def test_added_file_refused(self):
        r,f,out=self.publish();(out/'unrequested').write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError,'intake_inventory'):self.verify(out)
    def test_symlink_refused(self):
        r,f,out=self.publish();(out/'link').symlink_to(self.source/'package.json')
        with self.assertRaisesRegex(ValueError,'intake_inventory'):self.verify(out)
    def test_external_receipt_binding_required(self):
        r,f,out=self.publish()
        with self.assertRaisesRegex(ValueError,'intake_receipt_binding'):self.verify(out,'0'*64)
    def test_source_reverified(self):
        r,f,out=self.publish();(self.source/'unchanged').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'fixture_source_changed'):self.verify(out)
    def test_wrong_source_pin_refused(self):
        self.sha='0'*64
        with self.assertRaisesRegex(ValueError,'fixture_source_digest'):self.build()
    def test_placement_purpose_refused(self):
        with self.assertRaisesRegex(ValueError,'review_intake_purpose'):self.build(purpose='placement')
        r,f,out=self.publish()
        with self.assertRaisesRegex(ValueError,'review_intake_purpose'):self.verify(out,purpose='placement')
    def test_existing_output_preserved(self):
        r,f,out=self.publish()
        with self.assertRaisesRegex(ValueError,'new_output'):exporter.publish(out,f,sc)
        self.assertEqual((out/'files.json').read_bytes(),f['files.json'])
    def test_html_escapes_record_and_disables_network(self):
        r=self.reviewed();r['notes']='</script><script>bad()</script>';_,f=self.build(records.encode(r));self.assertNotIn(r['notes'].encode(),f['index.html']);self.assertIn(b"connect-src 'none'",f['index.html']);self.assertEqual(f[intake.FORM],b'fixture form')
if __name__=='__main__':unittest.main()
