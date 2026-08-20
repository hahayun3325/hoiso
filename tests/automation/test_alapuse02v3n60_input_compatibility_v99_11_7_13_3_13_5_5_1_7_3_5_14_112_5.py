import importlib.util, json, os, sys, tempfile, unittest
from pathlib import Path

source=Path(os.environ.get('TRACEHOI_INPUT_ADAPTER_SOURCE', Path(__file__).parents[2]/'src/foho/automation/input_compatibility.py'))
spec=importlib.util.spec_from_file_location('tracehoi_input_compatibility',source)
module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)

class InputCompatibilityTest(unittest.TestCase):
    def setUp(self): self.manifest=Path(os.environ['TRACEHOI_INPUT_MANIFEST'])
    def test_exact_three_roles_and_hashes(self):
        p=module.load_runtime_input(self.manifest)
        self.assertTrue(p.rgb.is_file()); self.assertTrue(p.object_mask.is_file()); self.assertTrue(p.hand_mask.is_file())
        self.assertEqual(len({p.rgb,p.object_mask,p.hand_mask}),3)
    def test_out_of_split_cannot_enter_official_aggregate(self):
        p=module.load_runtime_input(self.manifest)
        self.assertFalse(p.official_1000_member); self.assertFalse(p.aggregate_with_official_1000)
    def test_tampered_hash_is_rejected(self):
        data=json.loads(self.manifest.read_text()); data['inputs']['rgb']['sha256']='0'*64
        with tempfile.TemporaryDirectory() as d:
            q=Path(d)/'manifest.json'; q.write_text(json.dumps(data))
            with self.assertRaises(module.InputContractError): module.load_runtime_input(q)

if __name__=='__main__': unittest.main()
