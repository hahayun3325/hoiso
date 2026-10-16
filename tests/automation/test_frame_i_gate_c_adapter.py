import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import trimesh

from foho.automation.frame_i_gate_c_adapter import FrameIGateCError, run_frame_i, run_gate_c


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def record(path):
    return {"path": str(path), "sha256": sha(path)}


class FrameIGateCAdapterTests(unittest.TestCase):
    def fixture(self, root):
        screen = trimesh.creation.box(extents=(2.0, 0.1, 1.0))
        screen.apply_translation((0.0, 0.0, 0.6))
        base = trimesh.creation.box(extents=(2.0, 1.0, 0.1))
        whole = trimesh.util.concatenate((screen, base))
        angle = np.deg2rad(20.0)
        rotation = np.array([[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
        matrix = np.eye(4)
        matrix[:3, :3] = 1.5 * rotation
        matrix[:3, 3] = (0.2, -0.3, 2.0)
        reference = whole.copy()
        reference.apply_transform(matrix)
        paths = {}
        for name, mesh in (("whole_object", whole), ("screen_lid", screen), ("keyboard_base", base), ("reference", reference)):
            path = root / f"{name}.ply"
            mesh.export(path)
            paths[name] = path
        hand = trimesh.creation.icosphere(subdivisions=3, radius=0.15)
        hand.apply_translation(reference.centroid + (0.0, 0.0, 0.3))
        hand_path = root / "hand.ply"
        hand.export(hand_path)
        patch_map = root / "patch_map.json"
        patch_map.write_text(json.dumps({"parts": {"screen_lid": {"regions": {"upper_left_top_rim": {"face_ids": [0, 1, 2, 3]}}}}}))
        finger_map = root / "finger_map.json"
        finger_map.write_text("{}")
        binding = root / "binding.json"
        binding.write_text(json.dumps({
            "schema": "tracehoi.FreshGateAToFrameIGateCBindingSpec.v1",
            "decision": "fresh_gate_A_frame_I_gate_C_binding_spec_closed",
            "historical_face_ids_reused": False,
            "active_object_part": "screen_lid",
            "fresh_whole_object": record(paths["whole_object"]),
            "fresh_part_owners": {"screen_lid": record(paths["screen_lid"]), "keyboard_base": record(paths["keyboard_base"])},
            "historical_reference_owners": {
                "frame_I_object_reference": record(paths["reference"]),
                "historical_object_patch_map": record(patch_map),
                "historical_finger_map": record(finger_map),
                "hand_in_I": record(hand_path),
            },
        }))
        config = root / "config.json"
        config.write_text(json.dumps({
            "schema": "tracehoi.FreshFrameIGateCConfig.v1",
            "case_id": "alapuse02v3n60",
            "owners": {"binding_spec": record(binding)},
            "semantic_contract": {
                "selected_hand_identity": "upper_image_hand",
                "active_fingers": ["index", "middle"],
                "object_part": "screen_lid",
                "object_region_key": "upper_left_top_rim",
            },
            "finger_tip_vertex_ids": {"index": 10, "middle": 20},
            "registration_policy": {
                "sample_count": 1000,
                "seed": 7,
                "trim_fraction": 0.8,
                "max_iterations": 20,
                "tolerance": 1e-9,
                "scale_min": 0.1,
                "scale_max": 10.0,
                "similarity_singular_ratio_max": 1.000001,
                "correspondence_normalized_mean_max": 0.02,
                "normalized_symmetric_mean_max": 0.05,
                "normalized_symmetric_p95_max": 0.10,
            },
            "patch_policy": {
                "min_faces": 2,
                "max_screen_fraction": 0.9,
                "normalized_mapping_p95_max": 0.5,
                "largest_component_ratio_min": 0.25,
            },
            "gate_c_policy": {
                "hand_object_diagonal_ratio_min": 0.001,
                "hand_object_diagonal_ratio_max": 2.0,
                "active_tip_target_normalized_max": 10.0,
                "target_preference_margin": 10.0,
            },
        }))
        return config, paths

    def test_frame_i_and_gate_c_are_zero_update_and_fresh_topology(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config, _ = self.fixture(root)
            frame = run_frame_i(config, root / "frame")
            self.assertEqual(frame["decision"], "alapuse02v3n60_fresh_frame_I_closed")
            self.assertFalse(frame["historical_face_ids_reused"])
            self.assertEqual(frame["optimization_updates"], 0)
            gate = run_gate_c(config, root / "frame/frame_i_terminal.json", root / "gate_c")
            self.assertEqual(gate["decision"], "alapuse02v3n60_fresh_gate_C_zero_update_closed")
            self.assertEqual(gate["active_fingers"], ["index", "middle"])
            self.assertEqual(gate["optimization_updates"], 0)

    def test_tampered_fresh_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config, paths = self.fixture(root)
            paths["screen_lid"].write_bytes(paths["screen_lid"].read_bytes() + b"tamper")
            with self.assertRaises(FrameIGateCError):
                run_frame_i(config, root / "frame")


if __name__ == "__main__":
    unittest.main(verbosity=2)


from unittest import mock


class AcceptedLidPublicationTests(unittest.TestCase):
    def accepted_fixture(self, root):
        screen = trimesh.creation.box(extents=(2.0, 0.1, 1.0))
        screen.apply_translation((0.0, 0.0, 1.0))
        keyboard = trimesh.creation.box(extents=(2.0, 1.0, 0.1))
        whole = trimesh.util.concatenate((screen, keyboard))
        paths = {}
        for name, mesh in (("whole_object", whole), ("screen_lid", screen), ("keyboard_base", keyboard), ("reference", whole.copy())):
            path = root / f"{name}.ply"
            mesh.export(path)
            paths[name] = path
        old_hand = trimesh.creation.icosphere(subdivisions=2, radius=0.1)
        old_hand_path = root / "old_hand.ply"
        old_hand.export(old_hand_path)
        patch_map = root / "patch.json"
        patch_map.write_text(json.dumps({"parts": {"screen_lid": {"regions": {"upper_left_top_rim": {"face_ids": [0, 1]}}}}}))
        finger_map = root / "fingers.json"
        finger_map.write_text("{}")
        binding_path = root / "binding.json"
        binding = {
            "schema": "tracehoi.FreshGateAToFrameIGateCBindingSpec.v1",
            "decision": "fresh_gate_A_frame_I_gate_C_binding_spec_closed",
            "historical_face_ids_reused": False,
            "active_object_part": "screen_lid",
            "fresh_whole_object": record(paths["whole_object"]),
            "fresh_part_owners": {"screen_lid": record(paths["screen_lid"]), "keyboard_base": record(paths["keyboard_base"])},
            "historical_reference_owners": {
                "frame_I_object_reference": record(paths["reference"]),
                "historical_object_patch_map": record(patch_map),
                "historical_finger_map": record(finger_map),
                "hand_in_I": record(old_hand_path),
            },
        }
        binding_path.write_text(json.dumps(binding))
        rng = np.random.default_rng(7)
        vertices = rng.normal(0.0, 0.045, size=(778, 3)) + np.array([-0.90, 0.10, 1.45])
        vertices[10] = np.array([-0.95, 0.08, 1.45])
        vertices[20] = np.array([-0.85, 0.08, 1.45])
        joints = vertices[:21].copy()
        candidate_path = root / "candidate.npz"
        np.savez(candidate_path, aligned_vertices_moge_Nx3=vertices, aligned_joints_moge_21x3=joints)
        topology_vertices = rng.normal(size=(778, 3))
        topology_faces = np.asarray([[0, index, index + 1] for index in range(1, 777)], dtype=np.int64)
        topology_path = root / "topology.ply"
        trimesh.Trimesh(vertices=topology_vertices, faces=topology_faces, process=False).export(topology_path)
        h2m_path = root / "h2m.npy"
        np.save(h2m_path, np.eye(4, dtype=np.float64))
        evidence_path = root / "evidence.json"
        evidence_path.write_text(json.dumps({
            "decision": "hand_specific_frame_I_cpu_adequate_lid_proximity_evidence_closed",
            "part_preference": {"screen_lid_preference_passed": True},
        }))
        review_path = root / "review.json"
        review_path.write_text(json.dumps({
            "decision": "hand_specific_frame_I_cpu_adequate_lid_proximity_review_accepted",
            "review": {"label": "accepted_near_screen_lid"},
        }))
        spec_path = root / "publication_spec.json"
        spec = {
            "schema": "tracehoi.HandSpecificFrameIAcceptedLidPublicationReentrySpec.v1",
            "decision": "hand_specific_frame_I_accepted_lid_publication_and_reentry_spec_closed",
            "errors": [],
            "accepted_review": record(review_path),
            "accepted_machine_evidence": record(evidence_path),
            "accepted_hand_candidate": record(candidate_path),
            "MANO_topology_owner": record(topology_path),
            "object_route": {
                "H2M": record(h2m_path),
                "fresh_sources": {
                    "whole_object": record(paths["whole_object"]),
                    "screen_lid": record(paths["screen_lid"]),
                    "keyboard_base": record(paths["keyboard_base"]),
                },
            },
            "superseded_live_owners": {"binding_spec": record(binding_path)},
        }
        spec_path.write_text(json.dumps(spec))
        config_path = root / "config.json"
        config = {
            "schema": "tracehoi.FreshFrameIGateCConfig.v1",
            "case_id": "alapuse02v3n60",
            "owners": {"binding_spec": record(binding_path), "accepted_lid_publication_spec": record(spec_path)},
            "semantic_contract": {
                "selected_hand_identity": "upper_image_hand",
                "active_fingers": ["index", "middle"],
                "object_part": "screen_lid",
                "object_region_key": "upper_left_top_rim",
            },
            "finger_tip_vertex_ids": {"index": 10, "middle": 20},
            "registration_policy": {
                "sample_count": 100, "seed": 7, "trim_fraction": 0.8, "max_iterations": 2, "tolerance": 1e-9,
                "scale_min": 0.1, "scale_max": 10.0, "similarity_singular_ratio_max": 1.000001,
                "correspondence_normalized_mean_max": 0.02, "normalized_symmetric_mean_max": 0.05,
                "normalized_symmetric_p95_max": 0.10,
            },
            "patch_policy": {"min_faces": 1, "max_screen_fraction": 1.0, "normalized_mapping_p95_max": 1.0, "largest_component_ratio_min": 0.0},
            "gate_c_policy": {
                "hand_object_diagonal_ratio_min": 0.01,
                "hand_object_diagonal_ratio_max": 0.8,
                "active_tip_target_normalized_max": 0.3,
                "target_preference_margin": 0.0,
            },
        }
        config_path.write_text(json.dumps(config))
        return {
            "config": config_path, "config_packet": config, "spec": spec_path, "spec_packet": spec,
            "review": review_path, "candidate": candidate_path, "h2m": h2m_path,
            "vertices": vertices, "paths": paths,
        }

    def refresh_spec(self, fixture):
        fixture["spec"].write_text(json.dumps(fixture["spec_packet"]))
        fixture["config_packet"]["owners"]["accepted_lid_publication_spec"] = record(fixture["spec"])
        fixture["config"].write_text(json.dumps(fixture["config_packet"]))

    def test_accepted_review_closes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = self.accepted_fixture(root)
            frame = run_frame_i(fixture["config"], root / "runtime")
            self.assertTrue(frame["eligible_for_gate_c"])
            self.assertEqual(frame["registration"]["method"], "accepted_cpu_lid_proximity_v1")
            self.assertTrue(frame["accepted_lid_publication"]["full_part_precheck"]["each_active_tip_prefers_screen_lid"])

    def test_rejected_review_fails_without_terminal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = self.accepted_fixture(root)
            review = json.loads(fixture["review"].read_text())
            review["review"]["label"] = "rejected_not_near_screen_lid"
            fixture["review"].write_text(json.dumps(review))
            fixture["spec_packet"]["accepted_review"] = record(fixture["review"])
            self.refresh_spec(fixture)
            with self.assertRaises(FrameIGateCError):
                run_frame_i(fixture["config"], root / "runtime")
            self.assertFalse((root / "runtime/frame_i_terminal.json").exists())

    def test_published_mesh_has_owned_topology_and_binding_rebind(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = self.accepted_fixture(root)
            frame = run_frame_i(fixture["config"], root / "runtime")
            binding = json.loads(Path(frame["binding_spec"]["path"]).read_text())
            hand_record = binding["historical_reference_owners"]["hand_in_I"]
            self.assertEqual(hand_record, frame["accepted_lid_publication"]["published_hand"])
            hand = trimesh.load_mesh(hand_record["path"], process=False)
            self.assertEqual(len(hand.vertices), 778)
            self.assertEqual(len(hand.faces), 776)

    def test_h2m_transforms_three_objects_never_hand_and_bypasses_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = self.accepted_fixture(root)
            matrix = np.eye(4, dtype=np.float64)
            np.save(fixture["h2m"], matrix)
            fixture["spec_packet"]["object_route"]["H2M"] = record(fixture["h2m"])
            self.refresh_spec(fixture)
            module = __import__("foho.automation.frame_i_gate_c_adapter", fromlist=["unused"])
            original_transform = module.transform_mesh
            with mock.patch.object(module, "estimate_similarity", side_effect=AssertionError("historical similarity called")), \
                 mock.patch.object(module, "remap_patch", side_effect=AssertionError("historical remap called")), \
                 mock.patch.object(module, "transform_mesh", wraps=original_transform) as transformed:
                frame = run_frame_i(fixture["config"], root / "runtime")
            self.assertEqual(transformed.call_count, 3)
            self.assertFalse(frame["transform"]["applies_to_hand"])
            hand = trimesh.load_mesh(frame["accepted_lid_publication"]["published_hand"]["path"], process=False)
            self.assertTrue(np.allclose(np.asarray(hand.vertices), fixture["vertices"], atol=1e-6))

    def test_old_partial_runtime_artifact_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = self.accepted_fixture(root)
            sentinel = root / "runtime/artifacts/old_failed_frame_i.txt"
            sentinel.parent.mkdir(parents=True)
            sentinel.write_text("preserve-me")
            run_frame_i(fixture["config"], root / "runtime")
            self.assertEqual(sentinel.read_text(), "preserve-me")

    def test_gate_c_recomputes_full_part_metrics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = self.accepted_fixture(root)
            run_frame_i(fixture["config"], root / "runtime")
            gate = run_gate_c(fixture["config"], root / "runtime/frame_i_terminal.json", root / "gate")
            self.assertEqual(gate["metrics"]["target_geometry"], "full_screen_lid_vertices")
            self.assertTrue(gate["metrics"]["each_active_tip_prefers_screen_lid"])

    def test_gate_c_rejects_keyboard_preference_or_invalid_scale(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = self.accepted_fixture(root)
            run_frame_i(fixture["config"], root / "runtime")
            bad = {
                "hand_to_object_diagonal_ratio": 0.2,
                "active_tip_target_normalized_max": 0.1,
                "each_active_tip_prefers_screen_lid": False,
            }
            module = __import__("foho.automation.frame_i_gate_c_adapter", fromlist=["unused"])
            with mock.patch.object(module, "_accepted_full_part_metrics", return_value=bad):
                with self.assertRaises(FrameIGateCError):
                    run_gate_c(fixture["config"], root / "runtime/frame_i_terminal.json", root / "gate_keyboard")
            config = json.loads(fixture["config"].read_text())
            config["gate_c_policy"]["hand_object_diagonal_ratio_min"] = 0.9
            fixture["config"].write_text(json.dumps(config))
            with self.assertRaises(FrameIGateCError):
                run_gate_c(fixture["config"], root / "runtime/frame_i_terminal.json", root / "gate_scale")

    def test_hash_failure_writes_no_terminal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = self.accepted_fixture(root)
            fixture["candidate"].write_bytes(fixture["candidate"].read_bytes() + b"tamper")
            with self.assertRaises(FrameIGateCError):
                run_frame_i(fixture["config"], root / "runtime")
            self.assertFalse((root / "runtime/frame_i_terminal.json").exists())


def test_accepted_metadata_rich_fresh_records_normalize_without_metadata_loss(self):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        fixture = self.accepted_fixture(root)
        binding_path = Path(fixture["config_packet"]["owners"]["binding_spec"]["path"])
        binding = json.loads(binding_path.read_text())
        for role in ("screen_lid", "keyboard_base"):
            binding["fresh_part_owners"][role].update({
                "connected_components": 1,
                "faces": 12 if role == "screen_lid" else 18,
                "vertices": 8 if role == "screen_lid" else 10,
            })
        binding_path.write_text(json.dumps(binding))
        fixture["config_packet"]["owners"]["binding_spec"] = record(binding_path)
        fixture["spec_packet"]["superseded_live_owners"]["binding_spec"] = record(binding_path)
        self.refresh_spec(fixture)
        frame = run_frame_i(fixture["config"], root / "runtime")
        self.assertTrue(frame["eligible_for_gate_c"])
        preserved = json.loads(binding_path.read_text())["fresh_part_owners"]
        self.assertEqual(preserved["screen_lid"]["vertices"], 8)
        self.assertEqual(preserved["keyboard_base"]["faces"], 18)


def test_accepted_different_valid_fresh_owner_keeps_identity_guard(self):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        fixture = self.accepted_fixture(root)
        binding_path = Path(fixture["config_packet"]["owners"]["binding_spec"]["path"])
        binding = json.loads(binding_path.read_text())
        alternate = root / "alternate_screen_lid.ply"
        alternate.write_bytes(fixture["paths"]["screen_lid"].read_bytes())
        binding["fresh_part_owners"]["screen_lid"] = record(alternate)
        binding_path.write_text(json.dumps(binding))
        fixture["config_packet"]["owners"]["binding_spec"] = record(binding_path)
        fixture["spec_packet"]["superseded_live_owners"]["binding_spec"] = record(binding_path)
        self.refresh_spec(fixture)
        with self.assertRaisesRegex(FrameIGateCError, "accepted_fresh_source_owner"):
            run_frame_i(fixture["config"], root / "runtime")
        self.assertFalse((root / "runtime/frame_i_terminal.json").exists())
        self.assertFalse((root / "runtime/accepted_cpu_lid_proximity_v1").exists())


def test_accepted_fresh_hash_validation_precedes_mesh_loading(self):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        fixture = self.accepted_fixture(root)
        fixture["paths"]["screen_lid"].write_bytes(
            fixture["paths"]["screen_lid"].read_bytes() + b"\n"
        )
        module = __import__("foho.automation.frame_i_gate_c_adapter", fromlist=["unused"])
        with mock.patch.object(module, "load_mesh", side_effect=AssertionError("mesh load preceded owner validation")) as load_mesh_call:
            with self.assertRaises(FrameIGateCError):
                run_frame_i(fixture["config"], root / "runtime")
        load_mesh_call.assert_not_called()
        self.assertFalse((root / "runtime/frame_i_terminal.json").exists())
        self.assertFalse((root / "runtime/accepted_cpu_lid_proximity_v1").exists())


AcceptedLidPublicationTests.test_accepted_metadata_rich_fresh_records_normalize_without_metadata_loss = test_accepted_metadata_rich_fresh_records_normalize_without_metadata_loss
AcceptedLidPublicationTests.test_accepted_different_valid_fresh_owner_keeps_identity_guard = test_accepted_different_valid_fresh_owner_keeps_identity_guard
AcceptedLidPublicationTests.test_accepted_fresh_hash_validation_precedes_mesh_loading = test_accepted_fresh_hash_validation_precedes_mesh_loading

