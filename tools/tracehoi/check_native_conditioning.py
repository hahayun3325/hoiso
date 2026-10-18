import importlib.util,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('test_native_conditioning',root/'tests/geometry/test_native_conditioning.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(m));raise SystemExit(not r.wasSuccessful())
