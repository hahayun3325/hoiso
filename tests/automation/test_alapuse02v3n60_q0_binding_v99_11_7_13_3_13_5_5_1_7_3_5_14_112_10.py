from __future__ import annotations
import importlib.util, json, os, sys, tempfile, unittest
from pathlib import Path
def load_subject():
    path=Path(os.environ['TRACEHOI_Q0_BINDING_SOURCE']); spec=importlib.util.spec_from_file_location('tracehoi_q0_binding_candidate',path)
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); return module
class Q0BindingTest(unittest.TestCase):
    def setUp(self):
        self.subject=load_subject(); self.config=Path(os.environ['TRACEHOI_Q0_BINDING_CONFIG'])
        self.roots={'${PROJECT_ROOT}':os.environ['PROJECT_ROOT'],'${PHASE0_ROOT}':os.environ['PHASE0_ROOT']}
    def test_exact_real_input_and_transport(self):
        bound=self.subject.bind_q0(self.config,self.roots); receipt=self.subject.validation_receipt(bound)
        self.assertEqual(receipt['decision'],'real_input_Q0_binding_validate_only_closed')
        self.assertEqual(receipt['model'],'gpt-5.6-terra'); self.assertEqual(receipt['reasoning_effort'],'medium')
        self.assertFalse(receipt['store']); self.assertTrue(bound.crop.is_file())
        self.assertEqual(receipt['expected_output_sections'],['object_category','visible_geometry','foundation_primary','foundation_recovery','gate_b','gate_d0','confidence'])
    def test_tampered_owner_is_rejected(self):
        data=json.loads(self.config.read_text()); data['owners']['q0_design']['sha256']='0'*64
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'bad.json'; path.write_text(json.dumps(data))
            with self.assertRaises(self.subject.Q0BindingError): self.subject.bind_q0(path,self.roots)
if __name__=='__main__': unittest.main()
