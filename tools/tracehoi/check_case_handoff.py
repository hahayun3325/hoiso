"""Run geometry handoff regressions using only the Python standard library."""
import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def main():
    tests = [ROOT / 'tests/geometry/test_case_handoff.py']
    legacy = ROOT / 'tests/automation/test_moge_output_path_confinement_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_38.py'
    if legacy.exists():
        tests.append(legacy)
    suite = unittest.TestSuite()
    config = types.ModuleType('foho.configs')
    config.third_party_root = lambda: '/unused/third_party'
    # Do not import the installed foho configuration or any native dependency.
    package = types.ModuleType('foho')
    package.__path__ = [str(ROOT / 'src/foho')]
    with patch.dict(sys.modules, {'foho': package, 'foho.configs': config}), patch.dict(
        os.environ, {'MOGE_SOURCE': str(ROOT / 'src/foho/geometry/moge.py')}
    ):
        for index, path in enumerate(tests):
            spec = importlib.util.spec_from_file_location('handoff_suite_' + str(index), path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
