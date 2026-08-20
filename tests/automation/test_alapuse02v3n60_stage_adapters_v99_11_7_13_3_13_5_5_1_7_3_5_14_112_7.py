from __future__ import annotations
import hashlib, importlib.util, os, sys, tempfile, types, unittest
from pathlib import Path

def load_subject():
    source=Path(os.environ["TRACEHOI_STAGE_ADAPTER_SOURCE"])
    spec=importlib.util.spec_from_file_location("tracehoi_stage_adapter_candidate",source)
    module=importlib.util.module_from_spec(spec); assert spec and spec.loader
    spec.loader.exec_module(module); return module

class StageAdapterLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.subject=load_subject(); module=types.ModuleType("tracehoi_fake_stage")
        exec("def run(alpha, beta):\n    return alpha + beta\n",module.__dict__)
        sys.modules[module.__name__]=module
        self.owner={"module":module.__name__,"callable":"run","args":["alpha","beta"]}
    def tearDown(self):
        sys.modules.pop("tracehoi_fake_stage",None)
    def test_exact_signature_and_kwargs(self):
        self.subject.validate_owner(self.owner)
        self.assertEqual(self.subject.run_callable(self.owner,{"alpha":2,"beta":3}),5)
    def test_wrong_signature_and_kwargs_are_rejected(self):
        with self.assertRaises(self.subject.StageContractError):
            self.subject.validate_owner(dict(self.owner,args=["alpha"]))
        with self.assertRaises(self.subject.StageContractError):
            self.subject.run_callable(self.owner,{"alpha":2})
    def test_missing_and_tampered_input_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"input.bin"; path.write_bytes(b"accepted")
            receipt={"rgb":{"path":str(path),"sha256":hashlib.sha256(b"accepted").hexdigest()}}
            self.subject.require_inputs(receipt); path.write_bytes(b"tampered")
            with self.assertRaises(self.subject.StageContractError): self.subject.require_inputs(receipt)
            path.unlink()
            with self.assertRaises(self.subject.StageContractError): self.subject.require_inputs(receipt)
    def test_valid_handoff_and_missing_output(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); inp=root/"input.bin"; out=root/"output.bin"
            inp.write_bytes(b"input"); out.write_bytes(b"output")
            inputs={"previous":{"path":str(inp),"sha256":hashlib.sha256(b"input").hexdigest()}}
            packet=self.subject.handoff_receipt("fake",inputs,{"next":str(out)})
            self.assertEqual(packet["decision"],"stage_handoff_closed"); out.unlink()
            with self.assertRaises(self.subject.StageContractError):
                self.subject.handoff_receipt("fake",inputs,{"next":str(out)})

if __name__=="__main__": unittest.main()
