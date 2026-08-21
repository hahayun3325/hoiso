import importlib.util,os,unittest
def load(path):
    spec=importlib.util.spec_from_file_location("transport_under_test",path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
resolve=load(os.environ["HAND_TRANSPORT_SOURCE"]).resolve
class TransportTests(unittest.TestCase):
    def test_truth_table_and_spatial_preservation(self):
        for original,mirrored,want in ((False,False,False),(False,True,True),(True,False,True),(True,True,False)):
            got=resolve(spatial_instance="upper_image_hand",original_is_right=original,pixels_mirrored=mirrored)
            self.assertIs(got["canonical_is_right"],want)
            self.assertEqual(got["spatial_instance"],"upper_image_hand")
    def test_domains_are_separate(self):
        with self.assertRaises(ValueError):
            resolve(spatial_instance="right_upper",original_is_right=True,pixels_mirrored=False)
        with self.assertRaises(TypeError):
            resolve(spatial_instance="single_hand",original_is_right=1,pixels_mirrored=False)
if __name__=="__main__": unittest.main(verbosity=2)
