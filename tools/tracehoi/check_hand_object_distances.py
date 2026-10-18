"""Run deterministic geometry and distance-contract tests without native imports."""
import importlib.util,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('test_hand_object_distances',root/'tests/geometry/test_hand_object_distances.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(m));raise SystemExit(not result.wasSuccessful())
