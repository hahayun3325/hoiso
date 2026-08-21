from __future__ import annotations
import importlib.util, os, tempfile, unittest
from pathlib import Path

def load_module(name: str, path: Path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RuntimeError('cannot load '+str(path))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class ContractTest(unittest.TestCase):
    def setUp(self):
        self.manifest=Path(os.environ['MANIFEST_SOURCE'])
        self.q1=Path(os.environ['Q1_SOURCE'])
        self.q2=Path(os.environ['Q2_SOURCE'])
        self.note=Path(os.environ['NOTE_SOURCE'])
        for path in (self.manifest,self.q1,self.q2,self.note):
            self.assertTrue(path.is_file(),str(path))

    def test_manifest_splits_object_and_joint_inputs(self):
        text=self.manifest.read_text()
        moge=text[text.index("_stage('moge'"):text.index("_stage('hunyuan'")]
        hunyuan=text[text.index("_stage('hunyuan'"):text.index("_stage('hamer'")]
        self.assertIn("'input':cfg.cropped_hoi_wo_bckg_path",''.join(moge.split()))
        self.assertIn("'image_dir':cfg.masked_obj_path",''.join(hunyuan.split()))
        self.assertNotIn('cropped_hoi_wo_bckg_path',''.join(hunyuan.split()))

    def _runtime_prompt(self, module_path: Path, name: str) -> str:
        module=load_module(name,module_path)
        with tempfile.TemporaryDirectory() as folder:
            panel=Path(folder)/'tiny.png'; panel.write_bytes(b'prompt-builder-only')
            config={'case_id':'alapuse02v3n60','model':'mock',
                    'reasoning_effort':'low','max_output_tokens':32}
            request=module.request(config,panel,{})
        return request['input'][0]['content'][0]['text']

    def test_q1_runtime_semantics(self):
        module=load_module('candidate_q1_schema',self.q1)
        prompt=self._runtime_prompt(self.q1,'candidate_q1_prompt')
        self.assertIn('MoGe is joint observation-space scene/depth',prompt)
        self.assertIn('Hunyuan is the object-only geometry branch',prompt)
        enum=module.schema('alapuse02v3n60')['properties']['overall_decision']['enum']
        self.assertEqual(enum,['PASS','RETRY_ONE_OWNER','REJECT_CASE'])

    def test_q2_runtime_semantics(self):
        module=load_module('candidate_q2_schema',self.q2)
        prompt=self._runtime_prompt(self.q2,'candidate_q2_prompt')
        self.assertIn('MoGe is joint observation-space scene/depth',prompt)
        self.assertIn('Hunyuan is the object-only geometry branch',prompt)
        enum=module.schema('alapuse02v3n60')['properties']['overall_decision']['enum']
        self.assertEqual(enum,['PASS','REJECT_CASE'])
        self.assertIn('Q2 is terminal',prompt)

    def test_note_has_concrete_IO_and_no_placeholders(self):
        text=self.note.read_text()
        for token in ('~~~mermaid','INVALIDATED_BY_PIPELINE_CONTRACT',
                      'Hunyuan object-only carrier','MoGe joint scene/depth',
                      'Gate A -> frame I -> Gate C -> D0 -> H0 -> H1 -> O0 -> J0 -> F0'):
            self.assertIn(token,text)
        for placeholder in ('{head}','{verdict}','{route}','{audit_path}'):
            self.assertNotIn(placeholder,text)

if __name__=='__main__': unittest.main()
