from __future__ import annotations
import importlib.util, json, os, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from foho import automation as automation_package

def load_combined_subject():
    path=Path(os.environ['TRACEHOI_COMBINED_Q0_SOURCE'])
    spec=importlib.util.spec_from_file_location('foho.automation.combined_q0',path)
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module
    spec.loader.exec_module(module); automation_package.combined_q0=module
    return module
COMBINED=load_combined_subject()

def load_subject():
    path=Path(os.environ['TRACEHOI_COMBINED_Q0_RUNNER_SOURCE'])
    spec=importlib.util.spec_from_file_location('tracehoi_combined_q0_runner_candidate',path)
    module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module
    spec.loader.exec_module(module); return module
class FakeResponses:
    def __init__(self,response): self.response=response; self.calls=[]
    def create(self,**kwargs):
        self.calls.append(kwargs)
        if isinstance(self.response,BaseException): raise self.response
        return self.response
class FakeClient:
    def __init__(self,response): self.responses=FakeResponses(response)
class CombinedQ0RunnerTest(unittest.TestCase):
    def setUp(self):
        self.subject=load_subject()
        roots={'${PROJECT_ROOT}':os.environ['PROJECT_ROOT'],'${PHASE0_ROOT}':os.environ['PHASE0_ROOT'],'${CASE_ROOT}':os.environ['CASE_ROOT']}
        self.contract=COMBINED.load_contract(os.environ['TRACEHOI_COMBINED_Q0_CONFIG'],roots)
    def packet(self):
        consumers=self.contract.consumers
        return {'object_category':'laptop',
          'visible_geometry':{'articulated':True,'articulation_state':'OPEN','visible_parts':['screen','base'],'occlusion_summary':'hand near screen'},
          'foundation_primary':{name:['laptop'] for name in consumers},
          'foundation_recovery':{name:['open laptop'] for name in consumers},
          'gate_b':{},'gate_d0':{'alternative_hypothesis':'{\"contact\":\"screen_edge\"}'},'confidence':0.9}
    def response(self,packet=None,**changes):
        base={'id':'resp_mock','model':'gpt-5.5-2026-04-23','status':'completed',
          'output_text':json.dumps(packet if packet is not None else self.packet()),'output':[],
          'usage':{'input_tokens':5000,'input_tokens_details':{'cached_tokens':0},'output_tokens':1000,'total_tokens':6000}}
        base.update(changes); return base
    def test_valid_response_and_exact_request(self):
        client=FakeClient(self.response())
        with tempfile.TemporaryDirectory() as td:
            receipt=self.subject.execute(client,self.contract,td,transport_authorized=True)
            self.assertEqual(receipt['decision'],'alapuse02v3n60_combined_Q0_live_closed')
            self.assertEqual(len(client.responses.calls),1)
            req=client.responses.calls[0]
            self.assertEqual((req['model'],req['reasoning']['effort'],req['store']),('gpt-5.5-2026-04-23','high',False))
            self.assertEqual([x['type'] for x in req['input'][0]['content']],['input_text','input_image'])
            self.assertTrue(req['input'][0]['content'][1]['image_url'].startswith('data:image/'))
            self.assertTrue(req['text']['format']['strict'])
            self.assertTrue(Path(td,'combined_Q0_semantic_packet.json').is_file())
    def test_missing_foundation_consumer_is_rejected_after_telemetry(self):
        packet=self.packet(); packet['foundation_primary'].pop(self.contract.consumers[-1])
        client=FakeClient(self.response(packet))
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(self.subject.CombinedQ0RunnerError,'foundation_primary_keys'):
                self.subject.execute(client,self.contract,td,transport_authorized=True)
            self.assertTrue(Path(td,'response_telemetry.json').is_file())
            self.assertFalse(Path(td,'combined_Q0_semantic_packet.json').exists())
    def test_refusal_and_incomplete_are_rejected(self):
        cases=[self.response(status='incomplete',incomplete_details={'reason':'max_output_tokens'}),
          self.response(output=[{'content':[{'type':'refusal','refusal':'cannot comply'}]}])]
        for response in cases:
            with self.subTest(status=response.get('status'),output=response.get('output')):
                client=FakeClient(response)
                with tempfile.TemporaryDirectory() as td:
                    with self.assertRaises(self.subject.CombinedQ0RunnerError):
                        self.subject.execute(client,self.contract,td,transport_authorized=True)
                    self.assertTrue(Path(td,'response_telemetry.json').is_file())
                    self.assertEqual(len(client.responses.calls),1)
    def test_malformed_json_keeps_telemetry_before_validation(self):
        client=FakeClient(self.response(output_text='not json'))
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(self.subject.CombinedQ0RunnerError,'json:'):
                self.subject.execute(client,self.contract,td,transport_authorized=True)
            telemetry=Path(td,'response_telemetry.json'); receipt=Path(td,'execution_receipt.json')
            self.assertTrue(telemetry.is_file()); self.assertTrue(receipt.is_file())
            self.assertTrue(json.loads(receipt.read_text())['telemetry_written_before_validation'])
    def test_transport_exception_records_one_attempt(self):
        client=FakeClient(RuntimeError('synthetic_transport_failure'))
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(self.subject.CombinedQ0RunnerError,'transport:RuntimeError'):
                self.subject.execute(client,self.contract,td,transport_authorized=True)
            failure=json.loads(Path(td,'transport_exception.json').read_text())
            self.assertEqual(len(client.responses.calls),1)
            self.assertEqual(failure['api_calls'],1)
            self.assertEqual(failure['decision'],'review_combined_Q0_transport_exception')
            self.assertFalse(Path(td,'combined_Q0_semantic_packet.json').exists())
    def test_codec_writes_decoded_canonical_packet(self):
        client=FakeClient(self.response())
        with tempfile.TemporaryDirectory() as td:
            self.subject.execute(client,self.contract,td,transport_authorized=True)
            packet=json.loads((Path(td)/'combined_Q0_semantic_packet.json').read_text())
            self.assertEqual(packet['gate_d0']['alternative_hypothesis'],{'contact':'screen_edge'})
    def test_nullable_codec_preserves_null_in_canonical_packet(self):
        packet=self.packet(); packet['gate_d0']['alternative_hypothesis']=None
        client=FakeClient(self.response(packet))
        with tempfile.TemporaryDirectory() as td:
            self.subject.execute(client,self.contract,td,transport_authorized=True)
            saved=json.loads((Path(td)/'combined_Q0_semantic_packet.json').read_text())
            self.assertIsNone(saved['gate_d0']['alternative_hypothesis'])
    def test_malformed_codec_keeps_telemetry_and_blocks_packet(self):
        packet=self.packet(); packet['gate_d0']['alternative_hypothesis']='[]'
        client=FakeClient(self.response(packet))
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(self.subject.CombinedQ0RunnerError):
                self.subject.execute(client,self.contract,td,transport_authorized=True)
            root=Path(td)
            self.assertTrue((root/'response_telemetry.json').is_file())
            self.assertFalse((root/'combined_Q0_semantic_packet.json').exists())
            receipt=json.loads((root/'execution_receipt.json').read_text())
            self.assertTrue(any(value.startswith('codec:') for value in receipt['errors']))
if __name__=='__main__': unittest.main()
