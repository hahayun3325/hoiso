from __future__ import annotations
import hashlib, json, tempfile, unittest
from pathlib import Path
import importlib.util
import os
import sys
from pathlib import Path

_candidate_source=Path(os.environ["TRACEHOI_PILOT_DAG_SOURCE"])
_spec=importlib.util.spec_from_file_location("tracehoi_candidate_pilot_dag",_candidate_source)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"cannot load candidate DAG: {_candidate_source}")
_candidate=importlib.util.module_from_spec(_spec)
sys.modules[_spec.name]=_candidate
_spec.loader.exec_module(_candidate)
PipelineContractError=_candidate.PipelineContractError
RestartableCaseDAG=_candidate.RestartableCaseDAG
STAGE_ORDER=_candidate.STAGE_ORDER

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class PilotDAGLifecycleTest(unittest.TestCase):
    def fixture(self,root):
        owner=root/"owner.json"; owner.write_text("{}\n")
        owners={role:{"kind":"fixture","terminal_validator_required":True,
                      "records":[{"locator":str(owner),"sha256":digest(owner)}]}
                for role in ("combined_q0","gate_a","gate_c_auto_v2","gate_d0","f0")}
        bundle=root/"owners.json"
        bundle.write_text(json.dumps({"schema":"tracehoi.AutomaticSemanticOwnerBundles.v1",
          "owners":owners,"decision":"automatic_semantic_owner_bundles_closed_for_mocking"})+"\n")
        initial=root/"crop.png"; initial.write_bytes(b"accepted-crop")
        receipt={"cropped_rgb":{"path":str(initial),"sha256":digest(initial)}}
        return bundle,receipt

    def test_full_chain_is_restartable_and_hash_continuous(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); bundle,initial=self.fixture(root)
            dag=RestartableCaseDAG("alapuse02v3n60",root/"run",bundle,{})
            dag.start(initial); previous=initial
            for stage in STAGE_ORDER:
                def produce(stage_root,inputs,stage=stage):
                    self.assertEqual(inputs,previous)
                    artifact=stage_root/"artifact.json"
                    artifact.write_text(json.dumps({"stage":stage,"input_hashes":
                      {k:v["sha256"] for k,v in inputs.items()}})+"\n")
                    return {"accepted_artifact":str(artifact)}
                receipt=dag.run_stage(stage,produce); previous=receipt["outputs"]
            state=RestartableCaseDAG("alapuse02v3n60",root/"run",bundle,{}).resume()
            self.assertEqual(state["status"],"complete")
            self.assertEqual(state["next_index"],len(STAGE_ORDER))
            self.assertEqual(len(state["history"]),len(STAGE_ORDER))
            self.assertEqual(state["api_calls"],0); self.assertEqual(state["gpu_updates"],0)

    def test_wrong_case_tamper_and_failure_do_not_promote(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); bundle,initial=self.fixture(root)
            with self.assertRaises(PipelineContractError):
                RestartableCaseDAG("another_case",root/"bad",bundle,{})
            dag=RestartableCaseDAG("alapuse02v3n60",root/"run",bundle,{})
            dag.start(initial); Path(initial["cropped_rgb"]["path"]).write_bytes(b"tampered")
            with self.assertRaises(Exception):
                dag.run_stage(STAGE_ORDER[0],lambda stage_root,inputs:{})
            state=json.loads((root/"run/state.json").read_text())
            self.assertEqual(state["next_index"],0)

if __name__=="__main__": unittest.main()
