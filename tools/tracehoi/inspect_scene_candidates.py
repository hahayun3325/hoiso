"""Read a saved diagnostic scene without importing model packages."""
import importlib.util
from pathlib import Path

def load_reader():
    root=Path(__file__).resolve().parents[2]
    path=root/'src/foho/geometry/scene_candidates.py'
    spec=importlib.util.spec_from_file_location('tracehoi_scene_candidates',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

if __name__=='__main__':
    load_reader().main()
