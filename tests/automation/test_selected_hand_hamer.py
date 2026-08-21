import importlib.util,json,os,tempfile,unittest
from pathlib import Path

def load(path):
    spec=importlib.util.spec_from_file_location("selected_hand_hamer_candidate",path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

class Contract(unittest.TestCase):
    def setUp(self): self.m=load(os.environ["SELECTED_HAND_HAMER_SOURCE"])
    def inventory(self,root,right=True):
        root=Path(root); crop=root/"selected_crop.png"; crop.write_bytes(b"owned-crop")
        owner=root/"case_selected_hand_owner.json"
        payload={"decision":"Q0_selected_detector_to_hand_mask_closed","selected_hand_id":"hand-123",
          "canonical_is_right":right,"crop_detector_box":[30,10,60,40],
          "artifacts":{"crop":{"path":str(crop),"sha256":self.m.sha(crop)}}}
        owner.write_text(json.dumps(payload)); digest=self.m.sha(owner)
        inventory=root/"stage_inventory.json"
        inventory.write_text(json.dumps({"decision":"foundation_stage_artifact_inventory_closed",
          "output_roots":[{"files":[{"path":str(owner),"sha256":digest},
            {"path":str(crop),"sha256":self.m.sha(crop)}]}]}))
        return inventory
    def test_selected_crop_is_inventory_owned(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(self.m.selected_crop_from_inventory(self.inventory(td)).name,"selected_crop.png")
    def test_side_then_overlap_selects_one(self):
        with tempfile.TemporaryDirectory() as td:
            got=self.m.select_candidate(self.inventory(td,True),
              [[30,10,60,40],[31,11,59,39],[0,0,5,5]],[0,1,1])
            self.assertEqual(got["candidate_index"],1); self.assertEqual(got["selected_hand_id"],"hand-123")
    def test_missing_canonical_side_stops(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(self.m.SelectedHandHaMeRError):
                self.m.select_candidate(self.inventory(td,True),[[30,10,60,40]],[0])
    def test_ambiguous_same_side_stops(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(self.m.SelectedHandHaMeRError):
                self.m.select_candidate(self.inventory(td,True),
                  [[30,10,60,40],[30,10,60,40]],[1,1])
    def test_surfaces_use_inventory_owner(self):
        hamer=Path(os.environ["HAMER_SOURCE"]).read_text()
        manifest=Path(os.environ["MANIFEST_SOURCE"]).read_text()
        self.assertIn("selected_hand_inventory",hamer)
        self.assertIn("selected_crop_from_inventory(selected_hand_inventory)",hamer)
        self.assertIn("select_candidate(selected_hand_inventory,boxes,right)",hamer)
        self.assertIn("'selected_hand_inventory':str(inv['preprocess'])",manifest)
if __name__=="__main__": unittest.main(verbosity=2)
