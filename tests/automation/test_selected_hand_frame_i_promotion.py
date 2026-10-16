import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class HandSpecificFrameIPromotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner_path = Path(os.environ["CASE_RUNNER_SOURCE"])
        cls.manifest_path = Path(os.environ["FOUNDATION_MANIFEST_SOURCE"])
        cls.policy_path = Path(os.environ["HAND_FRAME_I_POLICY_SOURCE"])
        cls.runner = load_module("case_runner_promotion_under_test", cls.runner_path)

    def template(self, root):
        path = root / "foundation.env"
        path.write_text(
            "IMAGE_PATH=old.png\nBASE_DIR=/old\nGEMINI_RESPONSES=category.csv\n"
            "OBJECT_PROMPT_CSV=object.csv\nFLUX_PROMPT_CSV=flux.csv\n"
        )
        return path

    def arguments(self, root):
        image = root / "image.png"
        image.write_bytes(b"image")
        prompts = {}
        for role in ("category", "object", "flux"):
            path = root / f"{role}.csv"
            path.write_text(role)
            prompts[role] = str(path)
        return image, prompts

    def test_legacy_runtime_has_no_frame_i_override(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            template = self.template(root)
            image, prompts = self.arguments(root)
            output = root / "runtime.env"
            self.runner.runtime_config(
                template, "/old", str(root / "outputs"), image, prompts, output,
                hand_instance="single_hand",
            )
            text = output.read_text()
            self.assertNotIn("HAND_FRAME_I_SOLVER_SCRIPT", text)
            self.assertNotIn("HAND_FRAME_I_POLICY_TEMPLATE", text)
            self.assertIn("HAND_INSTANCE=single_hand", text)

    def test_exact_hash_owned_override_is_written(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            template = self.template(root)
            image, prompts = self.arguments(root)
            solver = root / "solver.py"
            policy = root / "policy.json"
            solver.write_text("pass\n")
            policy.write_text("{}\n")
            output = root / "runtime.env"
            self.runner.runtime_config(
                template, "/old", str(root / "outputs"), image, prompts, output,
                hand_frame_i={
                    "solver_script": {"path": str(solver), "sha256": sha(solver)},
                    "policy_template": {"path": str(policy), "sha256": sha(policy)},
                },
            )
            rows = dict(
                line.split("=", 1) for line in output.read_text().splitlines() if "=" in line
            )
            self.assertEqual(rows["HAND_FRAME_I_SOLVER_SCRIPT"], str(solver.resolve()))
            self.assertEqual(rows["HAND_FRAME_I_POLICY_TEMPLATE"], str(policy.resolve()))

    def test_missing_override_owner_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            template = self.template(root)
            image, prompts = self.arguments(root)
            with self.assertRaises(RuntimeError):
                self.runner.runtime_config(
                    template, "/old", str(root / "outputs"), image, prompts,
                    root / "runtime.env",
                    hand_frame_i={"solver_script": {"path": "missing", "sha256": "bad"}},
                )

    def test_override_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            template = self.template(root)
            image, prompts = self.arguments(root)
            solver = root / "solver.py"
            policy = root / "policy.json"
            solver.write_text("pass\n")
            policy.write_text("{}\n")
            with self.assertRaises(RuntimeError):
                self.runner.runtime_config(
                    template, "/old", str(root / "outputs"), image, prompts,
                    root / "runtime.env",
                    hand_frame_i={
                        "solver_script": {"path": str(solver), "sha256": "0" * 64},
                        "policy_template": {"path": str(policy), "sha256": sha(policy)},
                    },
                )

    def test_manifest_contract_and_installed_policy_remain_safe(self):
        manifest = self.manifest_path.read_text()
        self.assertIn("HAND_FRAME_I_SOLVER_SCRIPT", manifest)
        self.assertIn("HAND_FRAME_I_POLICY_TEMPLATE", manifest)
        self.assertIn("mano_registration_solver", manifest)
        self.assertIn("mano_registration_policy", manifest)
        self.assertIn("run_v3_CPU_7DoF_global_hand_alignment", manifest)
        self.assertIn("alapuse02v3n60_selected_hand_CPU_7DoF.json", manifest)
        policy = json.loads(self.policy_path.read_text())
        self.assertIs(policy["candidate_execution_authorized"], False)
        self.assertIs(policy["authorizes_installation"], False)
        self.assertIs(policy["authorizes_frame_i"], False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
