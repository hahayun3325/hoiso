import sys,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tests/geometry'));sys.path.insert(0,str(root/'src/foho/geometry'))
suite=unittest.defaultTestLoader.discover(str(root/'tests/geometry'),pattern='test_mask_validation.py')
result=unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
