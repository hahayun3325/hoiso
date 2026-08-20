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
        self.assertEqual((receipt['model'],receipt['reasoning_effort'],receipt['store']),('gpt-5.6-terra','medium',False))
        self.assertTrue(self.contract.crop.is_file())
        gate_b=Path(data['owners']['gate_b_prompt']['path_template'].replace('${PROJECT_ROOT}',os.environ['PROJECT_ROOT']))
        gate_d0=Path(data['owners']['gate_d0_schema']['path_template'].replace('${PROJECT_ROOT}',os.environ['PROJECT_ROOT']))
        raw_gate_b=json.loads(gate_b.read_text())['output_schema']
        raw_gate_d0=json.loads(gate_d0.read_text())
        compiled_gate_b=self.contract.output_schema['properties']['gate_b']
        compiled_gate_d0=self.contract.output_schema['properties']['gate_d0']
        self.assertNotIn('type',raw_gate_b)
        self.assertNotIn('properties',raw_gate_b)
        self.assertEqual(compiled_gate_b['type'],'object')
        self.assertEqual(set(compiled_gate_b['properties']),set(raw_gate_b))
        def allows_null(node):
            value=node.get('type')
            return value=='null' or isinstance(value,list) and 'null' in value or any(allows_null(item) for key in ('anyOf','oneOf') for item in node.get(key,[]) or [])
        def audit(node,path):
            if not isinstance(node,dict): return
            self.assertTrue(set(node)&{'type','$ref','anyOf','oneOf'},path)
            self.assertFalse(set(node)&{'allOf','not','dependentRequired','dependentSchemas','if','then','else'},path)
            properties=node.get('properties')
            if properties is not None:
                self.assertEqual(node.get('type'),'object',path)
                self.assertIs(node.get('additionalProperties'),False,path)
                self.assertEqual(set(node.get('required',[])),set(properties),path)
                for name,child in properties.items(): audit(child,f'{path}.properties.{name}')
            if node.get('type')=='array': audit(node['items'],path+'.items')
            for key in ('anyOf','oneOf'):
                for index,child in enumerate(node.get(key,[]) or []): audit(child,f'{path}.{key}[{index}]')
            for name,child in (node.get('$defs',{}) or {}).items(): audit(child,f'{path}.$defs.{name}')
        audit(self.contract.output_schema,'root')
        raw_optional=set(raw_gate_d0.get('properties',{}))-set(raw_gate_d0.get('required',[]))
        for name in raw_optional:
            self.assertIn(name,compiled_gate_d0['required'])
            self.assertTrue(allows_null(compiled_gate_d0['properties'][name]),name)
        raw_contact=raw_gate_d0['properties']['contacts']['items']
        compiled_contact=compiled_gate_d0['properties']['contacts']['items']
        item_optional=set(raw_contact.get('properties',{}))-set(raw_contact.get('required',[]))
        for name in item_optional:
            self.assertIn(name,compiled_contact['required'])
            self.assertTrue(allows_null(compiled_contact['properties'][name]),'contacts.items.'+name)
    def test_missing_foundation_consumer_is_rejected(self):
        packet={key:{} for key in self.contract.output_schema['required']}
        packet.update({'object_category':'laptop','visible_geometry':{},'confidence':1.0,'gate_b':{},'gate_d0':{}})
        packet['foundation_primary']={name:['laptop'] for name in self.contract.consumers[:-1]}
        packet['foundation_recovery']={name:['laptop'] for name in self.contract.consumers}
        with self.assertRaisesRegex(self.subject.CombinedQ0Error,'foundation_primary_keys'): self.subject.validate_semantic_packet(packet,self.contract)
    def test_const_and_enum_only_leaves_receive_explicit_types(self):
        const=self.subject._compile_openai_transport_schema({'const':'semantic_v1'},'const_case')
        enum=self.subject._compile_openai_transport_schema({'enum':['OPEN','CLOSED',None]},'enum_case')
        self.assertEqual(const['type'],'string')
        self.assertEqual(enum['type'],['string','null'])
        gate_d0=self.contract.output_schema['properties']['gate_d0']
        self.assertEqual(gate_d0['properties']['schema']['type'],'string')
        self.assertEqual(self.subject.audit_openai_transport_schema(self.contract.output_schema),[])
    def test_transport_audit_rejects_an_untyped_leaf(self):
        gaps=self.subject.audit_openai_transport_schema({'description':'orphan'},'orphan',False)
        self.assertIn('orphan:missing_type_or_union',gaps)
    def test_nullable_open_object_codec_is_exact_and_reversible(self):
        self.assertEqual(self.contract.transport_codecs,
          {'gate_d0.alternative_hypothesis':'nullable_json_object_string'})
        node=self.contract.output_schema['properties']['gate_d0']['properties']['alternative_hypothesis']
        self.assertEqual(set(node['type']),{'string','null'})
        self.assertEqual(self.subject.audit_openai_transport_schema(self.contract.output_schema),[])
        encoded={'gate_d0':{'alternative_hypothesis':'{"contact":"screen_edge"}'}}
        decoded=self.subject.decode_transport_packet(encoded,self.contract)
        self.assertEqual(decoded['gate_d0']['alternative_hypothesis'],{'contact':'screen_edge'})
        self.assertIsInstance(encoded['gate_d0']['alternative_hypothesis'],str)
        nullable={'gate_d0':{'alternative_hypothesis':None}}
        self.assertIsNone(self.subject.decode_transport_packet(nullable,self.contract)
                          ['gate_d0']['alternative_hypothesis'])
    def test_nullable_open_object_codec_rejects_bad_nonnull_values(self):
        for raw in ('not-json','[]','null','3','true'):
            with self.subTest(raw=raw), self.assertRaises(self.subject.CombinedQ0Error):
                self.subject.decode_transport_packet(
                  {'gate_d0':{'alternative_hypothesis':raw}},self.contract)
if __name__=='__main__': unittest.main()
