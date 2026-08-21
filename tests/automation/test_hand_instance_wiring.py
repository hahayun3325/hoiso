import os, unittest
from pathlib import Path

class HandInstanceWiringTests(unittest.TestCase):
    def test_exact_transport_chain_is_present(self):
        root = Path(os.environ["HAND_CAND_ROOT"])
        expected = {
          "src/foho/automation/case_runner.py": ["select_hand_instance", "HAND_INSTANCE"],
          "src/foho/automation/foundation_manifest.py": ["raw_config['HAND_INSTANCE']"],
          "src/foho/preprocess/get_hunyuan_input.py": ["hand_instance=args.hand_instance"],
          "src/foho/preprocess/segment_hoi_sam2.py": ["select_hand_index", "[\"only hand\"]"],
        }
        for rel, needles in expected.items():
            text = (root / rel).read_text()
            for needle in needles:
                self.assertIn(needle, text, msg=rel + ":" + needle)

if __name__ == "__main__": unittest.main()
