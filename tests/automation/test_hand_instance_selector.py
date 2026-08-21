import importlib.util, os, unittest

def load_owner():
    spec = importlib.util.spec_from_file_location("hand_selector_under_test",
                                                  os.environ["HAND_SELECTOR_SOURCE"])
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

class HandInstanceSelectorTests(unittest.TestCase):
    def setUp(self):
        owner = load_owner()
        self.HandInstanceSelectionError = owner.HandInstanceSelectionError
        self.select_hand_index = owner.select_hand_index
        self.upper = [10, 10, 30, 30]
        self.lower = [20, 70, 70, 110]
        self.object_box = [15, 60, 90, 125]

    def test_upper_owner_overrides_higher_object_iou(self):
        self.assertEqual(self.select_hand_index([self.upper, self.lower],
                         "upper_image_hand", self.object_box), 0)

    def test_lower_owner(self):
        self.assertEqual(self.select_hand_index([self.upper, self.lower],
                         "lower_image_hand", self.object_box), 1)

    def test_legacy_closest_is_explicit(self):
        self.assertEqual(self.select_hand_index([self.upper, self.lower],
                         "closest_to_object", self.object_box), 1)

    def test_ambiguous_does_not_guess(self):
        with self.assertRaises(self.HandInstanceSelectionError):
            self.select_hand_index([self.upper, self.lower], "ambiguous", self.object_box)

    def test_single_contract_rejects_two(self):
        with self.assertRaises(self.HandInstanceSelectionError):
            self.select_hand_index([self.upper, self.lower], "single_hand", self.object_box)

if __name__ == "__main__": unittest.main()
