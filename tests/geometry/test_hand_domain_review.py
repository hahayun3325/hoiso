import copy,hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'src/foho/geometry'/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=load('hand_domain_review');sc=load('scene_candidates');render=load('scene_review')
class Reader:
 def __init__(self,m,data):self.m=m;self.data=data
 def inspect_bundle(self,*args):return self.m,self.data
 def __getattr__(self,name):return getattr(sc,name)
class ReviewTests(unittest.TestCase):
 def fixture(self,path):
  png=render.rgb_png(bytes([50,60,70])*(512*512));data={'original_rgb':png};m={'case_id':'fixture','candidates':[{'id':c} for c in r.IDS]}
  (path/'scene.json').write_bytes(sc.encode(m));mp=sc.binding((path/'scene.json').read_bytes())
  audit=dict(schema='tracehoi.HandModelDomainAudit.v1',case_id='fixture',manifest_binding=mp,source_bindings={k:sc.binding(v) for k,v in data.items()},candidates=[],selected_candidate=None,accepted_scale=None)
  for k in ['placement_ready','mask_modified','source_geometry_modified','full_parent_acceptance','scale_identified','geometric_accuracy_verified','physical_contact_verified']:audit[k]=False
  for cid in r.IDS:audit['candidates'].append(dict(id=cid,accepted=False,placement_ready=False,mask_accuracy_verified=False,regions={k:dict(mask_pixels=1,predicted_pixels=1,intersection=1) for k in ['hand_side','boundary_band','beyond_boundary']},full_visible_hand_mask=dict(mask_pixels=3,predicted_pixels=3,intersection=3)))
  files={'audit.json':sc.encode(audit),'audit.md':b'fixture'}|{cid+'_domain.png':png for cid in r.IDS}
  for n,b in files.items():(path/n).write_bytes(b)
  receipt=dict(schema='tracehoi.HandDomainAuditFiles.v1',manifest_binding=mp,files={n:sc.binding(b) for n,b in files.items()});raw=sc.encode(receipt);(path/'files.json').write_bytes(raw)
  return m,data,audit,Reader(m,data),sc.binding(files['audit.json'])['sha256'],sc.binding(raw)['sha256']
 def build(self,path,fixture):
  m,data,a,reader,ash,fsh=fixture;return r.build_review(path/'scene.json',sc.binding((path/'scene.json').read_bytes())['sha256'],'fixture',path,ash,fsh,reader,render)
 def test_preserves_original_audit_and_produces_two_files(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td).resolve();f=self.fixture(p);report,files=self.build(p,f);self.assertEqual(report['audit'],f[2]);self.assertEqual(set(files),{'index.html','review.json'});self.assertFalse(report['placement_ready'])
 def check(self,key,value,error):
  with tempfile.TemporaryDirectory() as td:
   m,data,a,reader,*_=self.fixture(Path(td));a[key]=value
   with self.assertRaisesRegex(ValueError,error):r.validate_report(a,m,data,reader)
 def test_wrong_case_refused(self):self.check('case_id','wrong','audit_case')
 def test_changed_source_refused(self):self.check('source_bindings',{},'audit_sources')
 def test_accepted_scale_refused(self):self.check('accepted_scale',2.3,'audit_selection')
 def test_placement_refused(self):self.check('placement_ready',True,'audit_admission')
 def test_wrong_schema_refused(self):self.check('schema','unknown','audit_schema')
 def test_missing_candidates_refused(self):self.check('candidates',[],'audit_candidates')
 def test_region_conservation_checked(self):
  with tempfile.TemporaryDirectory() as td:
   m,data,a,reader,*_=self.fixture(Path(td));a['candidates'][0]['regions']['hand_side']['mask_pixels']=4
   with self.assertRaisesRegex(ValueError,'region_conservation'):r.validate_report(a,m,data,reader)
 def test_receipt_hash_checked(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td).resolve();f=list(self.fixture(p));f[-1]='0'*64
   with self.assertRaisesRegex(ValueError,'receipt_binding'):self.build(p,f)
 def test_audit_hash_checked(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td).resolve();f=list(self.fixture(p));f[-2]='0'*64
   with self.assertRaisesRegex(ValueError,'audit_binding'):self.build(p,f)
 def test_changed_image_refused(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td).resolve();f=self.fixture(p);(p/'primary_domain.png').write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'audit_file_binding'):self.build(p,f)
 def test_html_offline_and_embedded_text_escaped(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td).resolve();f=list(self.fixture(p));a=f[2];a['note']='</script><script>bad()</script>';raw=sc.encode(a);(p/'audit.json').write_bytes(raw);f[-2]=sc.binding(raw)['sha256']
   receipt=sc.parse((p/'files.json').read_bytes());receipt['files']['audit.json']=sc.binding(raw);raw=sc.encode(receipt);(p/'files.json').write_bytes(raw);f[-1]=sc.binding(raw)['sha256']
   _,files=self.build(p,f);html=files['index.html'];self.assertNotIn(a['note'].encode(),html);self.assertIn(b"connect-src 'none'",html);self.assertNotIn(b'fetch(',html);self.assertIn(b'Download review JSON',html)
if __name__=='__main__':unittest.main()
