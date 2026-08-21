import unittest
from foho.automation.case_runner import resolve_hand_instance

class Q0HandResolutionTests(unittest.TestCase):
    def test_ambiguous_plus_right_upper(self):
        got=resolve_hand_instance({'gate_b':{'hand_instance':'ambiguous'},
          'gate_d0':{'active_hand':'right_upper'}})
        self.assertEqual(got['resolved_hand_instance'],'upper_image_hand')
        self.assertEqual(got['resolution_owner'],'gate_d0.active_hand')
    def test_explicit_lower(self):
        got=resolve_hand_instance({'gate_b':{'hand_instance':'lower_image_hand'},
          'gate_d0':{'active_hand':'left_lower'}})
        self.assertEqual(got['resolved_hand_instance'],'lower_image_hand')
    def test_unresolved_ambiguity_stops(self):
        with self.assertRaises(RuntimeError):
            resolve_hand_instance({'gate_b':{'hand_instance':'ambiguous'},
              'gate_d0':{'active_hand':'handedness_uncertain'}})
    def test_conflict_stops(self):
        with self.assertRaises(RuntimeError):
            resolve_hand_instance({'gate_b':{'hand_instance':'upper_image_hand'},
              'gate_d0':{'active_hand':'left_lower'}})

if __name__=='__main__': unittest.main(verbosity=2)
