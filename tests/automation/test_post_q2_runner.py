import hashlib,json,tempfile,unittest
from pathlib import Path
from foho.automation.post_q2_contract import PostQ2ContractError
from foho.automation.post_q2_runner import STAGES,run_mock

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
class PostQ2RunnerTests(unittest.TestCase):
    def fixture(self,root):
        owners={}
        for role in ("combined_q0","gate_a","gate_c_auto_v2","gate_d0","f0"):
            path=root/(role+".txt"); path.write_text(role)
            owners[role]={"terminal_validator_required":True,
              "records":[{"locator":str(path),"sha256":sha(path)}]}
        bundle=root/'bundle.json'; bundle.write_text(json.dumps({
          "schema":"tracehoi.AutomaticSemanticOwnerBundles.v1",
          "decision":"automatic_semantic_owner_bundles_closed_for_mocking","owners":owners}))
        evidence={}
        for role in ("panel","get_hunyuan_input","inpaint","moge","hunyuan","hamer","h2m","mano_registration"):
            path=root/(role+".bin"); path.write_bytes(role.encode())
            evidence[role]={"path":str(path),"sha256":sha(path)}
        q2=root/'Q2.json'; q2.write_text(json.dumps({
          "schema":"tracehoi.Q2TerminalResult.v1","case_id":"alapuse02v3n60",
          "decision":"Q2_PASS","eligible_for_gate_a":True,
          "third_jury_call_allowed":False,"decoded":{"overall_decision":"PASS"},
          "evidence":evidence}))
        q1_result=root/'Q1.json'; q1_result.write_text(json.dumps({
          "schema":"tracehoi.Q1LiveResult.v1","decoded":{"overall_decision":"PASS"}}))
        q1=root/'foundation_pass.json'; q1.write_text(json.dumps({
          "schema":"tracehoi.FoundationTerminalPass.v1","case_id":"alapuse02v3n60",
          "source_round":"Q1","source_result":str(q1_result),
          "source_result_sha256":sha(q1_result),"Q2_calls_in_lineage":0,
          "decision":"foundation_terminal_pass_closed","eligible_for_gate_a":True,
          "errors":[],"evidence":evidence}))
        config=root/'config.json'; config.write_text(json.dumps({
          "schema":"tracehoi.PostQ2Config.v1","case_id":"alapuse02v3n60",
          "owner_bundle":str(bundle),"roots":{},"stage_order":list(STAGES)}))
        return config,q2,q1,q1_result
    def test_q2_interruption_and_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); config,q2,_,_=self.fixture(root); run=root/'run'
            first=run_mock(config,q2,run,3); self.assertEqual(first["next_index"],3)
            final=run_mock(config,q2,run); self.assertEqual(final["status"],"complete")
            self.assertEqual([row["stage"] for row in final["history"]],list(STAGES))
    def test_direct_q1_pass_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); config,_,q1,_=self.fixture(root)
            state=run_mock(config,q1,root/'run',1)
            self.assertEqual(state["next_index"],1)
            self.assertEqual(state["history"][0]["stage"],"gate_a")
    def test_nonpass_q2_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); config,q2,_,_=self.fixture(root); packet=json.loads(q2.read_text())
            packet["decision"]="Q2_REJECT_CASE"; packet["eligible_for_gate_a"]=False
            packet["decoded"]["overall_decision"]="REJECT_CASE"; q2.write_text(json.dumps(packet))
            with self.assertRaises(PostQ2ContractError): run_mock(config,q2,root/'run')
    def test_stale_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); config,_,q1,_=self.fixture(root); packet=json.loads(q1.read_text())
            Path(packet["evidence"]["panel"]["path"]).write_bytes(b"changed")
            with self.assertRaises(PostQ2ContractError): run_mock(config,q1,root/'run')
    def test_tampered_q1_source_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); config,_,q1,q1_result=self.fixture(root)
            q1_result.write_text(json.dumps({"decoded":{"overall_decision":"REJECT_CASE"}}))
            with self.assertRaises(PostQ2ContractError): run_mock(config,q1,root/'run')
if __name__=="__main__": unittest.main(verbosity=2)
