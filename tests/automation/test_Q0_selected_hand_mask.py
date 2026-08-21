import importlib.util,os,unittest
from pathlib import Path
def load(path):
    spec=importlib.util.spec_from_file_location("selected_hand_mask_candidate",path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
class Contract(unittest.TestCase):
    def test_second_proposal_wins_by_overlap(self):
        m=load(os.environ["SELECTED_HAND_MASK_SOURCE"])
        got=m.select_mask_proposal([[0,0,20,20],[100,100,150,150]],
                                   [105,105,148,148],minimum_iou=.1)
        self.assertEqual(got["selected_proposal_index"],1)
    def test_no_overlap_stops(self):
        m=load(os.environ["SELECTED_HAND_MASK_SOURCE"])
        with self.assertRaises(m.SelectedHandMaskError):
            m.select_mask_proposal([[0,0,10,10]],[100,100,120,120],minimum_iou=.1)
    def test_installed_source_no_longer_blindly_takes_first_mask(self):
        text=Path(os.environ["SEGMENT_SOURCE"]).read_text()
        start=text.index("def hoi_detector("); end=text.index("\ndef get_hoi_mask(",start)
        body=text[start:end]
        self.assertNotIn('pred_hand[0]["masks"][0]',body)
        self.assertIn('pred_hand[0]["masks"][selected_index]',body)
        self.assertIn('Q0_control_signal_to_detector_box_to_mask_IoU',body)
    def test_owner_is_written(self):
        text=Path(os.environ["PREPROCESS_SOURCE"]).read_text()
        self.assertIn('_selected_hand_owner.json',text)
        self.assertIn('selected_hand_id',text)
if __name__=="__main__": unittest.main(verbosity=2)
