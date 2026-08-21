import importlib.util,json,tempfile,unittest
from pathlib import Path
SOURCE=Path(__file__).parents[2]/'src/foho/automation/foundation_manifest_rebind.py'
SPEC=importlib.util.spec_from_file_location('rebinder',SOURCE); MOD=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MOD)
class RebindTest(unittest.TestCase):
  def fixture(self,root):
    old=root/'old'; new=root/'new'; old.mkdir(); new.mkdir(); old_csv=root/'old.csv'; new_csv=root/'new.csv'
    old_csv.write_text('old'); new_csv.write_text('new'); upstream=new/'upstream.bin'; upstream.write_bytes(b'upstream')
    manifest={'stages':[{'name':'first','inputs':[{'path':str(old_csv),'sha256':MOD.sha256(old_csv)}],
      'kwargs':{'runner_args':['conda','env',f'worker --csv {old_csv} --out {old}']},
      'expected_outputs':[{'path':str(old/'out.bin')}]},
      {'name':'second','inputs':[{'path':str(old/'upstream.bin'),'sha256':'stale'}],
      'kwargs':{'runner_args':['conda','env',f'worker --input {old}/upstream.bin']}}]}
    path=root/'manifest.json'; path.write_text(json.dumps(manifest)); return old,new,old_csv,new_csv,path
  def run_build(self,root,stage):
    old,new,old_csv,new_csv,path=self.fixture(root); out=root/'out.json'; receipt=root/'receipt.json'
    packet=MOD.build(path,out,receipt,stage,str(old),str(new),[(str(old_csv),str(new_csv))])
    return old,new,old_csv,new_csv,out,packet
  def test_external_path_hash_and_command_move_together(self):
    with tempfile.TemporaryDirectory() as directory:
      old,new,old_csv,new_csv,out,packet=self.run_build(Path(directory),'first'); data=json.loads(out.read_text())
      self.assertEqual(packet['decision'],'foundation_manifest_stage_rebind_closed')
      self.assertEqual(data['stages'][0]['inputs'][0]['path'],str(new_csv))
      self.assertEqual(data['stages'][0]['inputs'][0]['sha256'],MOD.sha256(new_csv))
      self.assertIn(str(new_csv),data['stages'][0]['kwargs']['runner_args'][2])
  def test_root_input_hash_refresh(self):
    with tempfile.TemporaryDirectory() as directory:
      old,new,_,_,out,packet=self.run_build(Path(directory),'second'); data=json.loads(out.read_text())
      self.assertEqual(packet['decision'],'foundation_manifest_stage_rebind_closed')
      self.assertEqual(data['stages'][0]['inputs'][0]['sha256'],MOD.sha256(new/'upstream.bin'))
  def test_stage_narrowing(self):
    with tempfile.TemporaryDirectory() as directory:
      *_,out,packet=self.run_build(Path(directory),'first'); self.assertEqual(len(json.loads(out.read_text())['stages']),1)
  def test_unknown_stage_rejected(self):
    with tempfile.TemporaryDirectory() as directory:
      *_,out,packet=self.run_build(Path(directory),'missing'); self.assertEqual(packet['decision'],'review_foundation_manifest_stage_rebind'); self.assertFalse(out.exists())
  def test_missing_input_rejected(self):
    with tempfile.TemporaryDirectory() as directory:
      root=Path(directory); old,new,old_csv,new_csv,path=self.fixture(root); (new/'upstream.bin').unlink()
      packet=MOD.build(path,root/'out.json',root/'receipt.json','second',str(old),str(new),[])
      self.assertEqual(packet['decision'],'review_foundation_manifest_stage_rebind')
if __name__=='__main__': unittest.main()
