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
            owners[role]={"terminal_validator_required":True,"records":[{"locator":str(path),"sha256":sha(path)}]}
        bundle=root/'bundle.json'; bundle.write_text(json.dumps({"schema":"tracehoi.AutomaticSemanticOwnerBundles.v1","decision":"automatic_semantic_owner_bundles_closed_for_mocking","owners":owners}))
        evidence={}
        for role in ("panel","get_hunyuan_input","inpaint","moge","hunyuan","hamer","h2m","mano_registration"):
            path=root/(role+".bin"); path.write_bytes(role.encode()); evidence[role]={"path":str(path),"sha256":sha(path)}
        q2=root/'Q2.json'; q2.write_text(json.dumps({"schema":"tracehoi.Q2TerminalResult.v1","decision":"Q2_PASS","eligible_for_gate_a":True,"evidence":evidence}))
        config=root/'config.json'; config.write_text(json.dumps({"schema":"tracehoi.PostQ2Config.v1","case_id":"alapuse02v3n60","owner_bundle":str(bundle),"roots":{},"stage_order":list(STAGES)}))
        return config,q2
    def test_interruption_and_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); config,q2=self.fixture(root); run=root/'run'
            first=run_mock(config,q2,run,3); self.assertEqual(first["next_index"],3)
            final=run_mock(config,q2,run); self.assertEqual(final["status"],"complete")
            self.assertEqual([row["stage"] for row in final["history"]],list(STAGES))
    def test_nonpass_q2_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); config,q2=self.fixture(root); packet=json.loads(q2.read_text())
            packet["decision"]="Q2_REJECT_CASE"; packet["eligible_for_gate_a"]=False; q2.write_text(json.dumps(packet))
            with self.assertRaises(PostQ2ContractError): run_mock(config,q2,root/'run')
    def test_stale_q2_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); config,q2=self.fixture(root); packet=json.loads(q2.read_text())
            Path(packet["evidence"]["panel"]["path"]).write_bytes(b"changed")
            with self.assertRaises(PostQ2ContractError): run_mock(config,q2,root/'run')
if __name__=="__main__": unittest.main(verbosity=2)
