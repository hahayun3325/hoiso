import csv, hashlib, importlib, importlib.util, json, os, sys, tempfile, unittest
from pathlib import Path
def load_owner():
    candidate=os.environ.get("TRACEHOI_COMPAT_SOURCE")
    if not candidate: return importlib.import_module("foho.automation.q0_followmyhold_compatibility")
    name="foho.automation.q0_followmyhold_compatibility"
    spec=importlib.util.spec_from_file_location(name,candidate)
    module=importlib.util.module_from_spec(spec); sys.modules[name]=module
    spec.loader.exec_module(module); return module
owner=load_owner(); Q0CompatibilityError=owner.Q0CompatibilityError; materialize=owner.materialize
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
class TestCompat(unittest.TestCase):
 def config(self,root,handoff):
  path=root/"c.json"; path.write_text(json.dumps({"q0_handoff_sha256":sha(handoff),
   "columns":["image_id","image_path","response"],"bindings":{
   "image_id":{"kind":"literal","value":"alapuse02v3n60"},
   "image_path":{"kind":"literal","value":"/crop.png"},
   "response":{"kind":"pointer","pointer":["primary_values","object_segmentation"],
               "codec":"comma_space_join_v1"}}})+"\n"); return path
 def test_object_keywords(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); handoff=root/"q.json"
   handoff.write_text(json.dumps({"primary_values":{"object_segmentation":["laptop","screen"]}})+"\n")
   output=root/"view.csv"; receipt=materialize(handoff,self.config(root,handoff),output)
   self.assertEqual(list(csv.DictReader(output.open()))[0]["response"],"laptop, screen")
   self.assertEqual(receipt["api_calls"],0)
 def test_unsafe_delimiter(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); handoff=root/"q.json"
   handoff.write_text(json.dumps({"primary_values":{"object_segmentation":["laptop, stand"]}})+"\n")
   with self.assertRaises(Q0CompatibilityError):
    materialize(handoff,self.config(root,handoff),root/"bad.csv")
if __name__=="__main__": unittest.main()
