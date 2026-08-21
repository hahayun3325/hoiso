import hashlib, importlib.util, json, os, tempfile, types, unittest
from pathlib import Path
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path); item=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item); return item
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
class Responses:
  def __init__(self,packet): self.packet=packet; self.kwargs=None
  def create(self,**kwargs):
    self.kwargs=kwargs
    return types.SimpleNamespace(id='resp_fixture',status='completed',model=kwargs['model'],
      output_text=json.dumps(self.packet),usage={'input_tokens':10,'output_tokens':20})
class RunnerTest(unittest.TestCase):
  def setUp(self): self.q1=module('q1_runner_test',os.environ['Q1_RUNNER_SOURCE'])
  def fixture(self,root):
    panel=root/'panel.png'; panel.write_bytes(b'png-fixture'); policy=root/'policy.json'; policy.write_text('{}\n')
    config=root/'config.json'; config.write_text(json.dumps({'case_id':'alapuse02v3n60','model':'fixture-model',
      'reasoning_effort':'medium','max_output_tokens':1000,'policy':{'path':str(policy),'sha256':sha(policy)}}))
    manifest=root/'manifest.json'; manifest.write_text(json.dumps({'panel_sha256':sha(panel)})); return config,panel,manifest
  def packet(self,decision='PASS'):
    rows=[{'stage':stage,'status':'PASS','confidence':.9,'evidence':'fixture'} for stage in self.q1.STAGES]
    return {'case_id':'alapuse02v3n60','overall_decision':decision,'stage_decisions':rows,
      'retry_owner':'none','recheck_required':False,'recommended_recovery_prompt':'','summary':'fixture'}
  def test_dry_run_is_zero_cost(self):
    with tempfile.TemporaryDirectory() as raw:
      root=Path(raw); config,panel,manifest=self.fixture(root); output=root/'dry.json'
      result=self.q1.run(config,panel,manifest,output,dry_run=True)
      self.assertEqual(result['api_calls'],0); self.assertNotIn('base64',output.read_text())
  def test_one_live_call_and_schema(self):
    with tempfile.TemporaryDirectory() as raw:
      root=Path(raw); config,panel,manifest=self.fixture(root); output=root/'live.json'
      responses=Responses(self.packet()); client=types.SimpleNamespace(responses=responses)
      result=self.q1.run(config,panel,manifest,output,client=client)
      self.assertEqual(result['decision'],'Q1_PASS'); self.assertEqual(result['api_calls'],1)
      self.assertFalse(responses.kwargs['store']); self.assertEqual(responses.kwargs['text']['format']['type'],'json_schema')
  def test_inconsistent_retry_is_rejected(self):
    packet=self.packet('RETRY_ONE_OWNER')
    with self.assertRaises(RuntimeError): self.q1.validate(packet,'alapuse02v3n60')
if __name__=='__main__': unittest.main()
