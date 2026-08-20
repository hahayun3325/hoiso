from __future__ import annotations
import importlib.util, json, os, sys, unittest
from pathlib import Path
def load_subject():
    path=Path(os.environ['TRACEHOI_COMBINED_Q0_SOURCE']); spec=importlib.util.spec_from_file_location('tracehoi_combined_q0_candidate',path)
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module); return module
class CombinedQ0Test(unittest.TestCase):
    def setUp(self):
        self.subject=load_subject(); self.config=Path(os.environ['TRACEHOI_COMBINED_Q0_CONFIG'])
        self.roots={'${PROJECT_ROOT}':os.environ['PROJECT_ROOT'],'${PHASE0_ROOT}':os.environ['PHASE0_ROOT'],'${CASE_ROOT}':os.environ['CASE_ROOT']}
        self.contract=self.subject.load_contract(self.config,self.roots)
    def test_exact_owners_schemas_and_validate_only_receipt(self):
        receipt=self.subject.validation_receipt(self.contract); data=json.loads(self.config.read_text())
        self.assertEqual(receipt['decision'],'alapuse02v3n60_combined_Q0_validate_only_closed')
        self.assertEqual((receipt['model'],receipt['reasoning_effort'],receipt['store']),('gpt-5.5-2026-04-23','high',False))
        self.assertTrue(self.contract.crop.is_file())
        gate_b=Path(data['owners']['gate_b_prompt']['path_template'].replace('${PROJECT_ROOT}',os.environ['PROJECT_ROOT']))
        gate_d0=Path(data['owners']['gate_d0_schema']['path_template'].replace('${PROJECT_ROOT}',os.environ['PROJECT_ROOT']))
        self.assertEqual(self.contract.output_schema['properties']['gate_b'],json.loads(gate_b.read_text())['output_schema'])
        self.assertEqual(self.contract.output_schema['properties']['gate_d0'],json.loads(gate_d0.read_text()))
    def test_missing_foundation_consumer_is_rejected(self):
        packet={key:{} for key in self.contract.output_schema['required']}
        packet.update({'object_category':'laptop','visible_geometry':{},'confidence':1.0,'gate_b':{},'gate_d0':{}})
        packet['foundation_primary']={name:['laptop'] for name in self.contract.consumers[:-1]}
        packet['foundation_recovery']={name:['laptop'] for name in self.contract.consumers}
        with self.assertRaisesRegex(self.subject.CombinedQ0Error,'foundation_primary_keys'): self.subject.validate_semantic_packet(packet,self.contract)
if __name__=='__main__': unittest.main()
