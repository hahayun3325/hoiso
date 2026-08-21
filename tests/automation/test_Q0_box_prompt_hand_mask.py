import importlib.util,os,unittest
from pathlib import Path
import numpy as np
def load(path):
    spec=importlib.util.spec_from_file_location("selected_hand_mask_candidate",path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
class FakeSAM:
    def __init__(self,wrong=False): self.wrong=wrong; self.box=None; self.image_contiguous=None
    def predict(self,image,box):
        self.box=np.asarray(box); self.image_contiguous=bool(np.asarray(image).flags.c_contiguous); mask=np.zeros((1,64,64),dtype=np.uint8)
        if self.wrong: mask[:,40:55,40:55]=1
        else: mask[:,10:31,10:31]=1
        return mask,np.asarray([.9]),np.zeros_like(mask,dtype=float)
class Contract(unittest.TestCase):
    def setUp(self): self.m=load(os.environ["SELECTED_HAND_MASK_SOURCE"])
    def test_Q0_box_is_the_SAM2_prompt(self):
        backend=FakeSAM(); mask,owner=self.m.segment_box_prompt(
            backend,np.zeros((64,64,3),dtype=np.uint8),[10,10,31,31],minimum_iou=.5)
        self.assertEqual(backend.box.tolist(),[[10.0,10.0,31.0,31.0]])
        self.assertEqual(owner["selection_method"],"Q0_selected_detector_box_to_SAM2_box_prompt")
        self.assertEqual(int(mask.sum()),441)
    def test_negative_stride_RGB_view_is_normalized(self):
        base=np.zeros((64,64,3),dtype=np.uint8); view=base[...,::-1]
        self.assertFalse(view.flags.c_contiguous)
        backend=FakeSAM(); self.m.segment_box_prompt(
            backend,view,[10,10,31,31],minimum_iou=.5)
        self.assertTrue(backend.image_contiguous)
    def test_wrong_box_mask_stops(self):
        with self.assertRaises(self.m.SelectedHandMaskError):
            self.m.segment_box_prompt(FakeSAM(True),np.zeros((64,64,3),dtype=np.uint8),
                                      [10,10,31,31],minimum_iou=.1)
    def test_live_surface_is_box_prompted(self):
        text=Path(os.environ["SEGMENT_SOURCE"]).read_text()
        start=text.index("def hoi_detector("); end=text.index("\ndef get_hoi_mask(",start)
        body=text[start:end]
        self.assertIn("sam_model.sam,crop_img_hoi,crop_detector_box",body)
        self.assertNotIn('["only hand"]',body)
        self.assertIn("Q0_selected_detector_box_to_SAM2_box_prompt",body)
if __name__=="__main__": unittest.main(verbosity=2)
