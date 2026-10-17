"""Run scene continuation contract tests without native dependencies."""
import importlib.util,sys,unittest
from pathlib import Path
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    tests=load('test_scene_readiness',root/'tests/geometry/test_scene_readiness.py')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    raise SystemExit(not result.wasSuccessful())
