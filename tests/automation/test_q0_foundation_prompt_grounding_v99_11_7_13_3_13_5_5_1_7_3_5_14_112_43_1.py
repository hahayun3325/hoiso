import importlib.util,json,tempfile,unittest
from pathlib import Path
MODULE_PATH=Path(__file__).parents[2]/'src/foho/automation/q0_foundation_prompt_grounding.py'
SPEC=importlib.util.spec_from_file_location('grounder',MODULE_PATH); MOD=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MOD)
class GroundingTest(unittest.TestCase):
    def packet(self): return {'object_category':'articulated laptop computer'}
    def handoff(self,values=None): return {'recovery_values':{'object_segmentation':values or ['screen assembly','base assembly','hinge']}}
    def test_category_first(self):
        category,values,text=MOD.compile_keywords(self.packet(),self.handoff())
        self.assertEqual(values[0],category); self.assertTrue(text.startswith('articulated laptop computer,'))
    def test_deduplicates(self):
        _,values,_=MOD.compile_keywords(self.packet(),self.handoff(['articulated laptop computer','hinge']))
        self.assertEqual(values,['articulated laptop computer','hinge'])
    def test_rejects_negative(self):
        with self.assertRaisesRegex(ValueError,'negative_keyword'): MOD.compile_keywords(self.packet(),self.handoff(['no stand']))
    def test_limit(self):
        with self.assertRaisesRegex(ValueError,'keyword_limit'): MOD.compile_keywords(self.packet(),self.handoff(['a','b','c','d','e','f','g','h']))
    def test_writes_CSV(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root); image=root/'alapuse02v3n60_cropped_hoi_1.png'; image.write_bytes(b'rgb')
            packet=root/'packet.json'; packet.write_text(json.dumps(self.packet()))
            handoff=root/'handoff.json'; handoff.write_text(json.dumps(self.handoff()))
            result=MOD.write_view(packet,handoff,'recovery',image,root/'view.csv',root/'receipt.json')
            self.assertEqual(result['decision'],'Q0_category_grounded_prompt_closed')
            self.assertIn('articulated laptop computer, screen assembly',(root/'view.csv').read_text())
if __name__=='__main__': unittest.main()
