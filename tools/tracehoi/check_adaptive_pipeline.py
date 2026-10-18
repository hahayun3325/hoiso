"""Run portable proximity verification and dashboard contract tests."""
import importlib.util,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('test_adaptive_pipeline',root/'tests/geometry/test_adaptive_pipeline.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(m));raise SystemExit(not r.wasSuccessful())
