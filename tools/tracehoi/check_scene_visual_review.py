"""Run numerical raster/image tests without native dependencies."""
import importlib.util,sys,unittest
from pathlib import Path
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    load('scene_review',root/'src/foho/geometry/scene_review.py')
    tests=load('test_scene_visual_review',root/'tests/geometry/test_scene_visual_review.py')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    raise SystemExit(not result.wasSuccessful())
