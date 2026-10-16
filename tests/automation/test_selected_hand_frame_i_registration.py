import importlib.util
import json
import os
import unittest
from pathlib import Path

import numpy as np


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HandSpecificFrameIContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solver_path = Path(os.environ["HAND_FRAME_I_SOLVER_SOURCE"])
        cls.adapter_path = Path(os.environ["SELECTED_HAND_REGISTRATION_SOURCE"])
        cls.config_path = Path(os.environ["HAND_FRAME_I_POLICY_SOURCE"])
        cls.solver = load_module("hand_frame_i_solver_under_test", cls.solver_path)
        cls.adapter = load_module("selected_registration_under_test", cls.adapter_path)
        cls.policy = json.loads(cls.config_path.read_text())

    def test_policy_is_non_null_and_non_authorizing(self):
        self.assertEqual(self.policy["schema"], "tracehoi.HandSpecificFrameIPolicy.v1")
        self.assertIs(self.policy["candidate_execution_authorized"], False)
        self.assertIs(self.policy["authorizes_frame_i"], False)
        self.assertIs(self.policy["authorizes_installation"], False)
        self.assertIsNotNone(self.policy["maximum_anchor_nrmse"])
        self.assertIsNotNone(self.policy["maximum_surface_nrmse"])

    def test_solver_interface_has_no_object_H2M_argument(self):
        text = self.solver_path.read_text()
        self.assertNotIn('parser.add_argument("--H2M"', text)
        self.assertNotIn("vertices_moge = apply_similarity(vertices, h2m", text)
        paths = {
            "candidate": Path("candidate.npy"),
            "target": Path("target.npz"),
            "points": Path("points.exr"),
            "mask": Path("mask.png"),
        }
        arguments = self.adapter.frame_i_solver_arguments(
            solver_script=self.solver_path,
            paths=paths,
            runtime_policy=Path("policy.json"),
            result=Path("result.npz"),
            report=Path("report.json"),
        )
        self.assertNotIn("--H2M", arguments)
        self.assertNotIn("--initialization", arguments)
        self.assertIn("--moge-points", arguments)
        self.assertIn("--hand-mask", arguments)

    def test_moge_channel_and_native_axis_decode(self):
        camera_xyz = np.asarray([[[0.25, -0.5, 2.0]]], dtype=np.float64)
        stored_bgr = camera_xyz[..., ::-1]
        got = self.solver.decode_moge_points(stored_bgr)
        expected = camera_xyz * np.asarray([1.0, -1.0, -1.0])
        np.testing.assert_allclose(got, expected, atol=1e-12)

    def test_metric_joint_anchors_follow_selected_mask(self):
        point_map = np.full((128, 128, 3), np.nan, dtype=np.float64)
        mask = np.zeros((128, 128), dtype=bool)
        target = np.stack((5 + 4 * np.arange(21), 7 + 4 * np.arange(21)), axis=1).astype(float)
        expected = []
        for index, (x, y) in enumerate(target.astype(int)):
            value = np.asarray([index, index + 1, -(index + 2)], dtype=float)
            point_map[y, x] = value
            mask[y, x] = True
            expected.append(value)
        anchors, indices, weights, pixels = self.solver.collect_joint_anchors(
            point_map,
            mask,
            target,
            np.ones(21, dtype=bool),
            np.linspace(0.5, 1.0, 21),
            radius=1,
            minimum=8,
        )
        np.testing.assert_allclose(anchors, np.asarray(expected))
        np.testing.assert_array_equal(indices, np.arange(21))
        np.testing.assert_allclose(pixels, target)
        self.assertTrue(np.all(weights > 0))

    def test_weighted_umeyama_recovers_positive_proper_similarity(self):
        rng = np.random.default_rng(7)
        source = rng.normal(size=(21, 3))
        rotation = self.solver.rotation_matrix(np.asarray([0.2, -0.1, 0.15]))
        scale = 2.4
        translation = np.asarray([0.3, -0.2, -1.7])
        target = scale * (source @ rotation.T) + translation
        got_scale, got_rotation, got_translation = self.solver.weighted_umeyama(
            source, target, np.linspace(0.4, 1.0, 21)
        )
        self.assertAlmostEqual(got_scale, scale, places=10)
        np.testing.assert_allclose(got_rotation, rotation, atol=1e-10)
        np.testing.assert_allclose(got_translation, translation, atol=1e-10)
        self.assertGreater(np.linalg.det(got_rotation), 0)

    def test_bounded_fit_uses_metric_anchors_and_recovers_sim3(self):
        width = height = 128
        focal = 100.0
        intrinsic = np.asarray(
            [[focal, 0, width / 2], [0, focal, height / 2], [0, 0, 1]],
            dtype=np.float64,
        )
        pixels = np.stack(
            (
                np.linspace(38, 90, 21),
                64 + 16 * np.sin(np.linspace(0, 2 * np.pi, 21)),
            ),
            axis=1,
        )
        depth = np.linspace(1.7, 2.3, 21)
        camera = np.stack(
            (
                (pixels[:, 0] - width / 2) * depth / focal,
                (pixels[:, 1] - height / 2) * depth / focal,
                depth,
            ),
            axis=1,
        )
        anchors = camera * np.asarray([1.0, -1.0, -1.0])
        scale_true = 2.2
        rotation_true = self.solver.rotation_matrix(np.asarray([0.18, -0.12, 0.08]))
        translation_true = np.asarray([0.15, -0.1, -1.9])
        raw_joints = ((anchors - translation_true) @ rotation_true) / scale_true
        raw_vertices = np.repeat(raw_joints, 5, axis=0)[:100]
        config = dict(self.policy)
        config["surface_support_weight"] = 0.01
        config["log_scale_prior_weight"] = 0.01
        parameter, result, facts = self.solver.fit_hand_similarity(
            vertices=raw_vertices,
            joints=raw_joints,
            anchors=anchors,
            anchor_indices=np.arange(21),
            anchor_weights=np.ones(21),
            target_pixels=pixels,
            metric_support=anchors,
            intrinsic=intrinsic,
            config=config,
        )
        self.assertTrue(result.success)
        aligned = self.solver.apply_similarity(raw_joints, parameter)
        rmse = float(np.sqrt(np.mean(np.sum((aligned - anchors) ** 2, axis=1))))
        self.assertLess(rmse / facts["support_diagonal"], 1e-5)
        self.assertGreater(float(np.exp(parameter[0])), 0)
        self.assertGreater(np.linalg.det(self.solver.rotation_matrix(parameter[1:4])), 0)

    def test_moge_intrinsic_owns_fit_when_hamer_camera_differs(self):
        height, width = 96, 128
        expected = np.asarray(
            [[119.0, 0.0, 63.5], [0.0, 121.0, 47.5], [0.0, 0.0, 1.0]],
            dtype=np.float64,
        )
        yy, xx = np.indices((height, width), dtype=np.float64)
        depth = 1.5 + 0.002 * xx + 0.003 * yy
        camera = np.stack(
            (
                (xx - expected[0, 2]) * depth / expected[0, 0],
                (yy - expected[1, 2]) * depth / expected[1, 1],
                depth,
            ),
            axis=2,
        )
        native = camera * np.asarray([1.0, -1.0, -1.0])
        recovered, facts = self.solver.recover_moge_intrinsic(native)
        np.testing.assert_allclose(recovered, expected, atol=1e-10)
        self.assertLessEqual(facts["pointmap_self_reprojection_rmse_px"], 1e-3)
        hamer_a = self.solver.camera_intrinsic(5000.0, np.asarray([width, height]))
        hamer_b = self.solver.camera_intrinsic(2500.0, np.asarray([width, height]))
        self.assertFalse(np.allclose(hamer_a, hamer_b))
        recovered_again, _ = self.solver.recover_moge_intrinsic(native)
        np.testing.assert_allclose(recovered_again, recovered, atol=0.0)
        source = self.solver_path.read_text()
        self.assertIn("intrinsic, intrinsic_recovery = recover_moge_intrinsic(point_map)", source)
        self.assertIn("intrinsic=intrinsic", source)
        self.assertIn("projected_anchors = project_native(aligned_anchors, intrinsic)", source)
        self.assertIn('"projection_camera_owner": "native_moge_point_map"', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
