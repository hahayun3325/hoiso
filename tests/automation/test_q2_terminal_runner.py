import importlib.util,json,os,tempfile,types,unittest
from pathlib import Path

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module); return module

Q2=load('q2_candidate',os.environ['Q2_CANDIDATE'])
CASE=load('case_candidate',os.environ['CASE_CANDIDATE'])

class Responses:
    def __init__(self,decoded): self.decoded=decoded
    def create(self,**kwargs):
        return types.SimpleNamespace(status='completed',output_text=json.dumps(self.decoded),
          id='resp_test',model=kwargs['model'],usage={'input_tokens':10,'output_tokens':10})
class Client:
    def __init__(self,decoded): self.responses=Responses(decoded)

class Tests(unittest.TestCase):
    def fixture(self,root):
        policy=root/'policy.json'; policy.write_text('{}')
        panel=root/'Q2.png'; panel.write_bytes(b'nonempty-panel')
        manifest=root/'Q2.json'; manifest.write_text(json.dumps({'panel_sha256':Q2.sha(panel)}))
        inventories={}
        for stage in Q2.STAGES:
            path=root/(stage+'.json')
            path.write_text(json.dumps({'decision':'foundation_stage_artifact_inventory_closed'}))
            inventories[stage]=str(path)
        config=root/'config.json'; config.write_text(json.dumps({'case_id':'alapuse02v3n60',
          'protocol_round':'Q2','model':'gpt-5.6-terra','reasoning_effort':'medium',
          'max_output_tokens':4000,'policy':{'path':str(policy),'sha256':Q2.sha(policy)},
          'inventories':inventories}))
        rows=[{'stage':stage,'status':'PASS','confidence':1.0,'evidence':'ok'} for stage in Q2.STAGES]
        decoded={'case_id':'alapuse02v3n60','overall_decision':'PASS',
          'stage_decisions':rows,'retry_owner':'none','recheck_required':False,
          'recommended_recovery_prompt':'','summary':'all pass'}
        return config,panel,manifest,decoded
    def test_dry_run_and_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); c,p,m,d=self.fixture(root)
            dry=Q2.run(c,p,m,root/'dry.json',dry_run=True)
            self.assertEqual(dry['decision'],'Q2_nonempty_zero_cost_dry_run_closed')
            live=Q2.run(c,p,m,root/'live.json',client=Client(d))
            self.assertEqual(live['schema'],'tracehoi.Q2TerminalResult.v1')
            self.assertTrue(live['eligible_for_gate_a']); self.assertFalse(live['third_jury_call_allowed'])
            CASE.validate_jury_result(live,'Q2')
    def test_terminal_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); c,p,m,d=self.fixture(root)
            d['overall_decision']='REJECT_CASE'; d['stage_decisions'][6]['status']='FAIL'
            live=Q2.run(c,p,m,root/'live.json',client=Client(d))
            self.assertEqual(live['decision'],'Q2_REJECT_CASE'); self.assertFalse(live['eligible_for_gate_a'])
            CASE.validate_jury_result(live,'Q2')
    def test_retry_and_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); c,p,m,d=self.fixture(root)
            d['overall_decision']='RETRY_ONE_OWNER'; d['retry_owner']='mano_registration'
            with self.assertRaises(RuntimeError): Q2.run(c,p,m,root/'bad.json',client=Client(d))
            Path(json.loads(c.read_text())['inventories']['hamer']).write_text('changed')
            with self.assertRaises(Exception): Q2.run(c,p,m,root/'tampered.json',dry_run=True)
    def test_old_q1_shape_cannot_be_q2(self):
        packet={'schema':'tracehoi.Q1LiveResult.v1','decoded':{'overall_decision':'PASS','retry_owner':'none'}}
        with self.assertRaises(RuntimeError): CASE.validate_jury_result(packet,'Q2')

if __name__=='__main__': unittest.main(verbosity=2)
