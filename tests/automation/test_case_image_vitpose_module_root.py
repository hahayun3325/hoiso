import importlib.util, os, tempfile, unittest
from pathlib import Path

SOURCE=Path(os.environ["VITPOSE_TARGET_SOURCE"])
spec=importlib.util.spec_from_file_location("target",SOURCE)
target=importlib.util.module_from_spec(spec); spec.loader.exec_module(target)

class ModuleRootTests(unittest.TestCase):
    def make_owner(self,root,body):
        root.mkdir(); (root/"vitpose_model.py").write_text(body)
    def test_constructor_sees_module_root_and_caller_is_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); owner=base/"owner"
            self.make_owner(owner,"from pathlib import Path\nclass ViTPoseModel:\n def __init__(self,device): self.cwd=str(Path.cwd()); self.device=device\n")
            before=Path.cwd(); model=target.load_vitpose_model(owner,"cpu")
            self.assertEqual(model.cwd,str(owner.resolve())); self.assertEqual(Path.cwd(),before)
    def test_exception_still_restores_caller(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory); owner=base/"owner"
            self.make_owner(owner,"class ViTPoseModel:\n def __init__(self,device): raise RuntimeError('boom')\n")
            before=Path.cwd()
            with self.assertRaisesRegex(RuntimeError,"boom"): target.load_vitpose_model(owner,"cpu")
            self.assertEqual(Path.cwd(),before)
if __name__=="__main__": unittest.main(verbosity=2)
