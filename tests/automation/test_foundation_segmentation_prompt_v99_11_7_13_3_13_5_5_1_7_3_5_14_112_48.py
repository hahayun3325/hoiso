import csv,importlib.util,json,tempfile,unittest
from pathlib import Path
SOURCE=Path(__file__).parents[2]/'src/foho/automation/foundation_segmentation_prompt.py'
SPEC=importlib.util.spec_from_file_location('surface',SOURCE); MOD=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MOD)
class SurfaceTest(unittest.TestCase):
  def files(self,root,category='articulated laptop computer'):
    packet=root/'packet.json'; packet.write_text(json.dumps({'object_category':category}))
    aliases=root/'aliases.json'; aliases.write_text(json.dumps({'aliases':{'articulated laptop computer':'laptop'}}))
    image=root/'alapuse02v3n60_cropped_hoi_1.png'; image.write_bytes(b'rgb')
    return packet,aliases,image
  def test_current_case_compiles_to_laptop(self):
    with tempfile.TemporaryDirectory() as directory:
      packet,aliases,_=self.files(Path(directory)); self.assertEqual(MOD.compile_label(packet,aliases)[1],'laptop')
  def test_unknown_category_fails_closed(self):
    with tempfile.TemporaryDirectory() as directory:
      packet,aliases,_=self.files(Path(directory),'unknown');
      with self.assertRaisesRegex(ValueError,'unknown_segmentation_category'): MOD.compile_label(packet,aliases)
  def test_comma_list_rejected(self):
    with tempfile.TemporaryDirectory() as directory:
      root=Path(directory); packet,aliases,_=self.files(root); aliases.write_text(json.dumps({'aliases':{'articulated laptop computer':'laptop, hinge'}}))
      with self.assertRaisesRegex(ValueError,'invalid_grounding_label'): MOD.compile_label(packet,aliases)
  def test_more_than_three_words_rejected(self):
    with tempfile.TemporaryDirectory() as directory:
      root=Path(directory); packet,aliases,_=self.files(root); aliases.write_text(json.dumps({'aliases':{'articulated laptop computer':'large open articulated laptop'}}))
      with self.assertRaisesRegex(ValueError,'grounding_label_not_short_scalar'): MOD.compile_label(packet,aliases)
  def test_exact_legacy_CSV(self):
    with tempfile.TemporaryDirectory() as directory:
      root=Path(directory); packet,aliases,image=self.files(root); out=root/'view.csv'; receipt=root/'receipt.json'
      result=MOD.write(packet,aliases,image,out,receipt); rows=list(csv.DictReader(out.open()))
      self.assertEqual(result['decision'],'foundation_single_label_segmentation_prompt_closed')
      self.assertEqual(list(rows[0]),['image_id','image_path','response']); self.assertEqual(rows[0]['response'],'laptop')
if __name__=='__main__': unittest.main()
