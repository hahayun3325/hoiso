import copy,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'src/foho/geometry'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
sc=load('scene_candidates');e=load('diagnostic_scene_export')
from scene_candidate_fixture import build as fixture
class RecordsFixture:
 def build(self,*args):return {},{'index.html':b'fixture form'}
class ReadyFixture:
 def evaluate(self,manifest,digest,case,review,sha,reader,*mods):
  reader.inspect_bundle(manifest,digest,case)
  raw=mods[-1];return dict(placement_ready=False,stages=[dict(id='diagnostic_export',available=True)],review=dict(state='missing' if raw is None else 'draft',input_binding=None if raw is None else reader.binding(raw)))
 def prepare_stage(self,manifest,digest,case,review,sha,reader,*mods,stage,candidate,record_raw):
  assert stage=='diagnostic_export'
  return dict(readiness=self.evaluate(manifest,digest,case,review,sha,reader,*mods,record_raw),scene=reader.load_candidate(manifest,expected_sha256=digest,expected_case_id=case,candidate_id=candidate,purpose='diagnostic'))
class ExportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.m,files=fixture()
  for n,b in files.items():
   p=self.root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  self.path=self.root/'handoff/scene.json';self.sha=sc.binding(self.path.read_bytes())['sha256'];self.review=self.root/'review';self.review.mkdir()
  rows={'index.html':b'fixture review','review.json':b'{}'}
  for n,b in rows.items():(self.review/n).write_bytes(b)
  (self.review/'files.json').write_bytes(sc.encode(dict(files={n:sc.binding(b) for n,b in rows.items()})))
  self.rsha=sc.binding((self.review/'files.json').read_bytes())['sha256'];self.ready=ReadyFixture();self.args=(self.path,self.sha,'alapuse02v3n60',self.review,self.rsha,sc,None,None,RecordsFixture(),self.ready)
 def tearDown(self):self.tmp.cleanup()
 def build(self,ids=None,purpose='diagnostic',raw=None):return e.build(*self.args,candidate_ids=sc.IDS if ids is None else ids,purpose=purpose,record_raw=raw)
 def write(self):
  p,f=self.build();out=self.root/'export';e.publish(out,f,sc);return p,f,out
 def verify(self,out,sha=None,purpose='diagnostic'):
  return e.verify(out,sha or sc.binding((out/'package.json').read_bytes())['sha256'],'alapuse02v3n60',sc,None,None,RecordsFixture(),self.ready,purpose=purpose)
 def test_full_mesh_bytes_and_identity_preserved(self):
  p,f=self.build();self.assertEqual(p['mesh_model_matrix'],sc.IDENTITY)
  for r in self.m['resources'].values():self.assertEqual(f['source/'+r['path']],(self.path.parent/r['path']).read_bytes())
 def test_roundtrip_after_relocation(self):
  p,f,out=self.write();renamed=self.root/'relocated';out.rename(renamed);r=self.verify(renamed);self.assertTrue(r['verified']);self.assertFalse(r['placement_ready'])
 def test_crossing_remains_visible_and_unaccepted(self):
  p,_=self.build();c=p['candidates'][1];self.assertEqual(c['collision_gate'],'blocked_transverse_crossing');self.assertIn('transverse_mesh_crossing',c['blockers']);self.assertFalse(c['accepted'])
 def test_explicit_subset_never_selects_candidate(self):
  p,_=self.build(['minimum_scale_refined']);self.assertEqual(p['export_candidate_ids'],['minimum_scale_refined']);self.assertIsNone(p['selected_candidate']);self.assertIsNone(p['accepted_scale'])
 def test_placement_build_refused(self):
  with self.assertRaisesRegex(ValueError,'diagnostic_purpose'):self.build(purpose='placement')
 def test_placement_verify_refused(self):
  _,_,out=self.write()
  with self.assertRaisesRegex(ValueError,'diagnostic_purpose'):self.verify(out,purpose='placement')
 def test_explicit_unique_ids_required(self):
  for ids in [[],['primary','primary'],['best'],('primary',)]:
   with self.assertRaisesRegex(ValueError,'explicit_unique'):self.build(ids)
 def test_stage_unavailable_refused(self):
  with patch.object(self.ready,'evaluate',return_value=dict(placement_ready=False,stages=[])):
   with self.assertRaisesRegex(ValueError,'diagnostic_stage'):self.build()
 def test_double_transform_refused(self):
  old=self.ready.prepare_stage
  def changed(*a,**k):
   out=old(*a,**k);out['scene']['hand_model_matrix']=[[2,0,0,0],[0,2,0,0],[0,0,2,0],[0,0,0,1]];return out
  with patch.object(self.ready,'prepare_stage',side_effect=changed):
   with self.assertRaisesRegex(ValueError,'double_transform'):self.build()
 def test_changed_source_refused(self):
  q=self.path.parent/'assets/object.ply';q.write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'resource_binding'):self.build()
 def test_changed_export_mesh_refused(self):
  _,_,out=self.write();q=out/'source/assets/object.ply';q.write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'export_file_binding'):self.verify(out)
 def test_added_file_refused(self):
  _,_,out=self.write();(out/'unrequested').write_text('keep')
  with self.assertRaisesRegex(ValueError,'export_inventory'):self.verify(out)
 def test_symlink_refused(self):
  _,_,out=self.write();(out/'link').symlink_to(self.path)
  with self.assertRaisesRegex(ValueError,'export_symlink'):self.verify(out)
 def test_expected_manifest_hash_required(self):
  _,_,out=self.write()
  with self.assertRaisesRegex(ValueError,'export_manifest_binding'):self.verify(out,'0'*64)
 def test_forged_admission_refused_even_with_new_manifest_hash(self):
  p,_,out=self.write();p['placement_ready']=True;(out/'package.json').write_bytes(sc.encode(p))
  with self.assertRaisesRegex(ValueError,'export_semantic'):self.verify(out)
 def test_forged_preview_refused_even_with_updated_file_hash(self):
  p,_,out=self.write();(out/'index.html').write_bytes(b'forged');p['files']['index.html']=sc.binding(b'forged');(out/'package.json').write_bytes(sc.encode(p))
  with self.assertRaisesRegex(ValueError,'export_semantic'):self.verify(out)
 def test_original_review_bytes_preserved(self):
  raw=b'{ "fixture": true }';p,f=self.build(raw=raw);self.assertEqual(f['human_review.json'],raw);self.assertEqual(p['review_input_binding'],sc.binding(raw))
 def test_existing_output_preserved(self):
  _,f,out=self.write();before=(out/'package.json').read_bytes()
  with self.assertRaisesRegex(ValueError,'new_output'):e.publish(out,f,sc)
  self.assertEqual(before,(out/'package.json').read_bytes())
 def test_parent_symlink_refused(self):
  _,f=self.build();q=self.root/'link';q.symlink_to(self.root,target_is_directory=True)
  with self.assertRaisesRegex(ValueError,'parent_route'):e.publish(q/'out',f,sc)
 def test_traversal_output_refused(self):
  with self.assertRaisesRegex(ValueError,'output_path'):e.publish(self.root/'out',{'../escape':b'x'},sc)
 def test_sampling_deterministic_and_bounded(self):
  v=[(i,2*i,3*i) for i in range(7000)];a=e.sample_vertices(v);self.assertEqual(a,e.sample_vertices(v));self.assertEqual(len(a['points']),6000);self.assertEqual(a['indices'][0],0);self.assertEqual(a['indices'][-1],6999);self.assertEqual(len(set(a['indices'])),6000)
 def test_small_mesh_sampling_lossless(self):
  v=[(1,2,3),(4,5,6)];self.assertEqual(e.sample_vertices(v)['points'],[[1,2,3],[4,5,6]]);self.assertEqual(e.sample_vertices(v,1)['indices'],[0])
 def test_invalid_sample_size_refused(self):
  for count in [0,6001,True,1.1]:
   with self.assertRaises(ValueError):e.sample_vertices([(0,0,0)],count)
 def test_html_data_escaped_and_network_disabled(self):
  raw=e.html(dict(note='</script><script>bad()</script>'));self.assertNotIn(b'</script><script>bad()',raw);self.assertIn(b"connect-src 'none'",raw);self.assertIn(b'pageshow',raw)
if __name__=='__main__':unittest.main()
