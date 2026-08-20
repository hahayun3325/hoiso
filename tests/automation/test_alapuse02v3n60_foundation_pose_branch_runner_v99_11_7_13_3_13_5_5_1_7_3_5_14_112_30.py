import hashlib, importlib, importlib.util, os, sys, tempfile, types, unittest
from pathlib import Path
def load_owner():
    candidate=os.environ.get("TRACEHOI_BRANCH_SOURCE")
    if not candidate: return importlib.import_module("foho.automation.foundation_pose_branch_runner")
    name="foho.automation.foundation_pose_branch_runner"
    spec=importlib.util.spec_from_file_location(name,candidate)
    module=importlib.util.module_from_spec(spec); sys.modules[name]=module
    spec.loader.exec_module(module); return module
producer=load_owner().producer
class TestBranch(unittest.TestCase):
 def test_reference_carry(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); old=root/"owner"; old.write_text("x")
   inputs={"owner":{"path":str(old),"sha256":hashlib.sha256(old.read_bytes()).hexdigest()}}
   spec={"carry_inputs":True,"reference":{"outputs":{"object_mesh_in_I":str(old)}}}
   output=producer(spec,{},"reference")(root/"stage",inputs)
   self.assertEqual(output["owner"],str(old))
   self.assertEqual(output["object_mesh_in_I"],str(old))
 def test_live_call(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); fake=types.ModuleType("tracehoi_fixture")
   fake.write=lambda path: Path(path).write_text("object")
   sys.modules["tracehoi_fixture"]=fake
   spec={"carry_inputs":False,"live":{"calls":[{"callable":"tracehoi_fixture:write",
    "kwargs":{"path":"${STAGE_ROOT}/o.ply"}}],"outputs":{"object_mesh_in_I":"${STAGE_ROOT}/o.ply"}}}
   output=producer(spec,{},"live")(root/"stage",{})
   self.assertTrue(Path(output["object_mesh_in_I"]).is_file())
if __name__=="__main__": unittest.main()
