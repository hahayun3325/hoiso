import copy,importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load(name,path=None):
 s=importlib.util.spec_from_file_location(name,path or ROOT/'src/foho/geometry'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=load('mask_review_record');sc=load('scene_candidates');renderer=load('scene_review');viewer=load('hand_domain_review')
old=load('old_tests',ROOT/'tests/geometry/test_hand_domain_review.py')
class RecordTests(unittest.TestCase):
 def setUp(self):self.ctx={'case_id':'fixture','review_binding':{'bytes':1,'sha256':'a'*64},'source_bindings':{'hand_mask':{'bytes':1,'sha256':'b'*64}}};self.r=r.blank(self.ctx)
 def reviewed(self):
  a=copy.deepcopy(self.r);a.update(state='reviewed',reviewer='Example reviewer',notes='Visible region checked; uncertainty remains.',decision='uncertain',reviewed_at='2026-10-17T18:00:00Z',original_image_inspected=True,provisional_mask_inspected=True);return a
 def finding(self):return dict(kind='mask_excess',candidate='mask_only',bbox_xyxy_inclusive=[1,2,3,4],note='check edge')
 def fails(self,a,error):
  with self.assertRaisesRegex((ValueError,TypeError),error):r.validate(a,self.ctx)
 def test_draft_is_pending(self):self.assertFalse(r.validate(self.r,self.ctx)['human_review_record_complete'])
 def test_completed_record_never_accepts_geometry(self):
  v=r.validate(self.reviewed(),self.ctx);self.assertTrue(v['human_review_record_complete']);self.assertTrue(v['mask_review_required']);self.assertFalse(v['placement_ready']);self.assertFalse(v['mask_accuracy_verified']);self.assertFalse(v['authorship_verified'])
 def test_all_acceptance_fields_rejected(self):
  for key in r.FALSE_FIELDS:
   a=self.reviewed();a[key]=True;self.fails(a,'forbidden_admission')
 def test_scale_and_candidate_selection_rejected(self):
  for key,val in [('accepted_scale',2.2),('selected_candidate','primary')]:
   a=self.reviewed();a[key]=val;self.fails(a,'forbidden_selection')
 def test_missing_or_extra_field(self):
  a=self.reviewed();a['unknown']=1;self.fails(a,'record_fields');a=self.reviewed();del a['notes'];self.fails(a,'record_fields')
 def test_wrong_schema(self):a=self.reviewed();a['schema']='other';self.fails(a,'record_schema')
 def test_wrong_image_binding(self):
  a=self.reviewed();a['context']['source_bindings']['hand_mask']['sha256']='c'*64;self.fails(a,'context_binding')
 def test_boolean_not_equivalent_to_binding_integer(self):
  a=self.reviewed();a['context']['review_binding']['bytes']=True;self.fails(a,'context_binding')
 def test_explicit_inspection_required(self):
  for key in ['original_image_inspected','provisional_mask_inspected']:
   a=self.reviewed();a[key]=False;self.fails(a,'inspection_required')
 def test_inspection_not_truthy_string(self):a=self.reviewed();a['original_image_inspected']='yes';self.fails(a,'original_image_inspected')
 def test_review_identity_and_summary_required(self):
  for key in ['reviewer','notes']:
   a=self.reviewed();a[key]=' ';self.fails(a,'review_identity_and_summary')
 def test_decision_pending_cannot_complete(self):a=self.reviewed();a['decision']='pending';self.fails(a,'decision_required')
 def test_needs_revision_requires_region(self):
  a=self.reviewed();a['decision']='needs_revision';self.fails(a,'revision_region_required');a['findings']=[self.finding()];self.assertEqual(r.validate(a,self.ctx)['annotation_count'],1)
 def test_date_calendar_and_utc(self):
  for date in ['2026-02-30T00:00:00Z','now','2026-10-17T18:00:00+00:00']:
   a=self.reviewed();a['reviewed_at']=date
   with self.assertRaises(ValueError):r.validate(a,self.ctx)
 def test_draft_has_no_review_timestamp(self):a=copy.deepcopy(self.r);a['reviewed_at']='2026-10-17T18:00:00Z';self.fails(a,'draft_time')
 def test_bounds_and_integer_rectangles(self):
  for box in [[-1,0,10,10],[0,0,512,5],[4,1,3,4],[True,0,4,4],[1.0,2,3,4],[1,2,3]]:
   a=self.reviewed();f=self.finding();f['bbox_xyxy_inclusive']=box;a['findings']=[f];self.fails(a,'finding_box')
 def test_single_pixel_and_full_crop_allowed(self):
  for box in [[0,0,511,511],[4,4,4,4]]:
   a=self.reviewed();f=self.finding();f['bbox_xyxy_inclusive']=box;a['findings']=[f];r.validate(a,self.ctx)
 def test_annotation_limit(self):a=self.reviewed();a['findings']=[self.finding()]*51;self.fails(a,'findings')
 def test_unknown_annotation_reference(self):
  a=self.reviewed();f=self.finding();f['candidate']='best';a['findings']=[f];self.fails(a,'finding_category')
 def test_text_limits_and_controls(self):
  for key,value in [('reviewer','x'*121),('notes','\x00'),('notes','x'*4001)]:
   a=self.reviewed();a[key]=value;self.fails(a,key)
 def test_duplicate_json_key_refused(self):
  with self.assertRaisesRegex(ValueError,'duplicate_key'):r.parse(b'{"state":"draft","state":"reviewed"}')
 def test_nonfinite_and_oversized_json_refused(self):
  for raw in [b'{"x": NaN}',b' '*131073]:
   with self.assertRaises(ValueError):r.parse(raw)
 def fixture(self,path):
  m,data,a,reader,*_=old.ReviewTests().fixture(path)
  data['hand_mask']=renderer.pgm(bytes([255])+bytes(512*512-1));a['source_bindings']={k:sc.binding(v) for k,v in data.items()}
  raw=sc.encode(a);(path/'audit.json').write_bytes(raw);rec=json.loads((path/'files.json').read_bytes());rec['files']['audit.json']=sc.binding(raw);(path/'files.json').write_bytes(sc.encode(rec))
  ash=sc.binding(raw)['sha256'];fsh=sc.binding((path/'files.json').read_bytes())['sha256']
  report,files=viewer.build_review(path/'scene.json','unused','fixture',path,ash,fsh,reader,renderer)
  d=path/'review';d.mkdir()
  for n,b in files.items():(d/n).write_bytes(b)
  (d/'files.json').write_bytes(sc.encode(dict(schema='tracehoi.HandDomainReviewFiles.v1',manifest_binding=report['manifest_binding'],files={n:sc.binding(b) for n,b in files.items()})))
  return reader,d,sc.binding((d/'files.json').read_bytes())['sha256']
 def test_build_preserves_viewer_and_embeds_blank_record(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td).resolve();reader,d,sha=self.fixture(p);report,files=r.build(p/'scene.json','unused','fixture',d,sha,reader,renderer,viewer)
   self.assertFalse(report['review_record_complete']);self.assertEqual(set(files),{'index.html','review_template.json','validation.json','context.json'})
   self.assertIn(b'Compare A',files['index.html']);self.assertIn(b'Download completed review',files['index.html']);self.assertIn(b"connect-src 'none'",files['index.html']);self.assertEqual(r.parse(files['review_template.json'])['findings'],[])
 def test_modified_saved_viewer_refused(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td).resolve();reader,d,sha=self.fixture(p);(d/'index.html').write_text('changed')
   with self.assertRaisesRegex(ValueError,'review_file_binding'):r.build(p/'scene.json','unused','fixture',d,sha,reader,renderer,viewer)
if __name__=='__main__':unittest.main()
