from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from foho.automation.contracts import canonical_sha256
from foho.automation.openai_query_adapter import MockQueryAdapter
from foho.automation.orchestrator import AutomaticQueryOrchestrator
from foho.automation.prompt_registry import PromptRegistry


def object_schema(properties,required):
    return {"type":"object","properties":properties,"required":required,
            "additionalProperties":False}


STRING={"type":"string"}
BRANCH=object_schema({"branch_id":STRING,"verdict":{"type":"string","enum":["PASS","RETRY","FAIL"]},
                      "reason_code":STRING,"evidence_regions":{"type":"array","items":STRING},
                      "retry_authorized":{"type":"boolean"}},
                     ["branch_id","verdict","reason_code","evidence_regions","retry_authorized"])
Q0=object_schema({"object_category":STRING,"visible_geometry":{"type":"array","items":STRING},
                  "foundation_primary":{"type":"array","items":STRING},
                  "foundation_recovery":{"type":"array","items":STRING},
                  "gate_b":object_schema({"contact":STRING},["contact"]),
                  "gate_d0":object_schema({"objective":STRING},["objective"]),
                  "confidence":{"type":"number"}},
                 ["object_category","visible_geometry","foundation_primary","foundation_recovery","gate_b","gate_d0","confidence"])
JURY=object_schema({"branches":{"type":"array","items":BRANCH},"terminal_drop":{"type":"boolean"}},
                   ["branches","terminal_drop"])
Q0_PACKET={"object_category":"laptop","visible_geometry":["open lid","base"],
           "foundation_primary":["laptop","open lid"],"foundation_recovery":["articulated laptop","visible base"],
           "gate_b":{"contact":"hand on upper-left display edge"},
           "gate_d0":{"objective":"preserve articulation and align contact"},"confidence":0.95}


class MockQueryCoreTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.crop=self.root/"crop.png"; self.crop.write_bytes(b"mock-crop")
        self.evidence=self.root/"evidence.png"; self.evidence.write_bytes(b"mock-evidence")
        self.prompts={"Q0":"combined crop contract","Q1":"judge primary evidence","Q2":"judge recovery evidence"}
        self.schemas={"Q0":Q0,"Q1":JURY,"Q2":JURY}

    def tearDown(self): self.temp.cleanup()

    def test_normal_route_uses_two_calls(self):
        q1={"branches":[{"branch_id":"hand","verdict":"PASS","reason_code":"ok",
                         "evidence_regions":["hand"],"retry_authorized":False}],"terminal_drop":False}
        adapter=MockQueryAdapter({"Q0":Q0_PACKET,"Q1":q1})
        runner=AutomaticQueryOrchestrator(adapter,self.root/"normal_receipts")
        result=runner.run(crop_path=self.crop,prompts=self.prompts,schemas=self.schemas,
                          run_foundations=lambda packet:{"hand":{"sha":"a"}},
                          build_evidence=lambda stage,outputs:(self.evidence,),
                          recover_foundations=lambda failed,q0,outputs:outputs)
        self.assertEqual(result.semantic_call_count,2)
        self.assertEqual(adapter.calls,["Q0","Q1"])
        self.assertFalse(result.terminal_drop)

    def test_recovery_route_uses_three_calls_and_freezes_accepted_branch(self):
        q1={"branches":[
            {"branch_id":"hand","verdict":"PASS","reason_code":"ok","evidence_regions":["hand"],"retry_authorized":False},
            {"branch_id":"object","verdict":"RETRY","reason_code":"mask","evidence_regions":["object"],"retry_authorized":True}],
            "terminal_drop":False}
        q2={"branches":[{"branch_id":"object","verdict":"PASS","reason_code":"fixed",
                         "evidence_regions":["object"],"retry_authorized":False}],"terminal_drop":False}
        adapter=MockQueryAdapter({"Q0":Q0_PACKET,"Q1":q1,"Q2":q2})
        runner=AutomaticQueryOrchestrator(adapter,self.root/"recovery_receipts")
        initial={"hand":{"sha":"immutable"},"object":{"sha":"bad"}}
        def recover(failed,q0,outputs):
            self.assertEqual(failed,["object"])
            return {"hand":outputs["hand"],"object":{"sha":"fixed"}}
        result=runner.run(crop_path=self.crop,prompts=self.prompts,schemas=self.schemas,
                          run_foundations=lambda packet:initial,
                          build_evidence=lambda stage,outputs:(self.evidence,),recover_foundations=recover)
        self.assertEqual(result.semantic_call_count,3)
        self.assertEqual(result.foundation_outputs["hand"],initial["hand"])
        self.assertFalse(result.terminal_drop)

    def test_prompt_policy_rejects_negative_or_multiline_foundation_text(self):
        owner=self.root/"owner.json"; owner.write_text("{}\n")
        import hashlib
        manifest=self.root/"registry.json"
        manifest.write_text(json.dumps({"owners":{"x":{"path":str(owner),"sha256":hashlib.sha256(owner.read_bytes()).hexdigest()}},
                                        "keyword_policy":{"max_keywords":4,"max_chars":40,
                                                          "reject_prefixes":["no ","without "]}}))
        registry=PromptRegistry(manifest)
        self.assertEqual(registry.render_keywords(["laptop","open lid"]),"laptop, open lid")
        with self.assertRaises(ValueError): registry.render_keywords(["laptop","no stand"])
        with self.assertRaises(ValueError): registry.render_keywords(["laptop\nopen"])

    def test_mock_receipts_never_contain_a_secret(self):
        adapter=MockQueryAdapter({"Q0":Q0_PACKET})
        from foho.automation.openai_query_adapter import QueryRequest
        result=adapter.query(QueryRequest("Q0","prompt",(self.crop,),"q0_packet",Q0))
        self.assertNotIn("OPENAI_API_KEY",json.dumps(result.receipt))
        self.assertEqual(result.receipt["output_sha256"],canonical_sha256(Q0_PACKET))


if __name__=="__main__": unittest.main()
