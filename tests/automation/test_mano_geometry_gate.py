import importlib.util, os, unittest
import numpy as np

def load_owner():
    spec = importlib.util.spec_from_file_location("mano_gate_under_test",
                                                  os.environ["MANO_GATE_SOURCE"])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

class ManoGeometryGateTests(unittest.TestCase):
    def setUp(self):
        owner = load_owner()
        self.ManoGeometryError = owner.ManoGeometryError
        self.audit_vertices = owner.audit_vertices

    def test_compact_volume_passes(self):
        rng = np.random.default_rng(7)
        points = rng.normal(size=(778, 3)) * np.array([0.08, 0.04, 0.02])
        result = self.audit_vertices(points)
        self.assertEqual(result["decision"], "mano_geometry_gate_closed")

    def test_sheet_like_elongation_fails(self):
        x = np.linspace(0, 10, 778)
        points = np.column_stack((x, 1e-2*np.sin(x), 1e-5*np.cos(x)))
        with self.assertRaises(self.ManoGeometryError):
            self.audit_vertices(points)

    def test_nonfinite_fails(self):
        points = np.ones((778, 3)); points[0, 0] = np.nan
        with self.assertRaises(self.ManoGeometryError):
            self.audit_vertices(points)

if __name__ == "__main__": unittest.main()
