"""Run the diagnostic scene contract suite using only the standard library."""
import importlib.util
from pathlib import Path
import sys,unittest

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module);return module

if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    load('scene_candidates',root/'src/foho/geometry/scene_candidates.py')
    load('scene_candidate_fixture',root/'tests/geometry/scene_candidate_fixture.py')
    module=load('test_scene_candidates',root/'tests/geometry/test_scene_candidates.py')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    raise SystemExit(not result.wasSuccessful())
