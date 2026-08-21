from __future__ import annotations
import importlib.util, os, tempfile, unittest
from pathlib import Path

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(str(path))
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

class MultiviewContractTest(unittest.TestCase):
    def setUp(self):
        self.panel=Path(os.environ['PANEL_SOURCE'])
        self.q1=Path(os.environ['Q1_SOURCE']); self.q2=Path(os.environ['Q2_SOURCE'])
        self.note=Path(os.environ['NOTE_SOURCE'])

    def _prompt(self,path,name):
        module=load(name,path)
        with tempfile.TemporaryDirectory() as folder:
            image=Path(folder)/'tiny.png'; image.write_bytes(b'prompt-only')
            config={'case_id':'alapuse02v3n60','model':'mock',
                    'reasoning_effort':'low','max_output_tokens':32}
            return module.request(config,image,{})['input'][0]['content'][0]['text']

    def test_mesh_tile_renders_one_labeled_three_view_asset(self):
        import ast
        text=self.panel.read_text()
        tree=ast.parse(text)
        owners=[node for node in tree.body if isinstance(node,ast.FunctionDef)
                and node.name=='mesh_tile']
        self.assertEqual(len(owners),1)
        constants={node.value for node in ast.walk(owners[0])
                   if isinstance(node,ast.Constant) and isinstance(node.value,str)}
        self.assertTrue({'XY','XZ','YZ'}.issubset(constants))
        self.assertIn("views=[('XY',0,1),('XZ',0,2),('YZ',1,2)]",''.join(text.split()))
        self.assertIn('one mesh | three orthographic views',text)

    def test_Q1_knows_cell_F_is_one_mesh(self):
        prompt=self._prompt(self.q1,'candidate_multiview_q1')
        self.assertIn('XY, XZ, and YZ orthographic projections of one Hunyuan mesh asset',prompt)
        self.assertIn('Do not interpret the three labeled columns as disconnected fragments',prompt)

    def test_Q2_uses_the_same_evidence_contract(self):
        prompt=self._prompt(self.q2,'candidate_multiview_q2')
        self.assertIn('XY, XZ, and YZ orthographic projections of one Hunyuan mesh asset',prompt)
        self.assertIn('Q2 is terminal',prompt)

    def test_note_records_presentation_invalidation(self):
        text=' '.join(self.note.read_text().split())
        for token in ('INVALIDATED_BY_EVIDENCE_PRESENTATION_CONTRACT',
                      'XY / XZ / YZ','one mesh asset','replacement Q1'):
            self.assertIn(token,text)

if __name__=='__main__': unittest.main()
