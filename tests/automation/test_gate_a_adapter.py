import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import trimesh

from foho.automation import gate_a_adapter as gate_a
from foho.automation import post_q2_runner as post


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


class GateAAdapterTests(unittest.TestCase):
    def fixture(self, root):
        project = root / "project"
        scripts = project / "scripts" / "phase2"
        source_scripts = Path(__file__).resolve().parents[2] / "scripts" / "phase2"
        for name in (
            "run_gate_a_partfield_vmap_merge_adapter.py",
            "check_gate_a_partfield_vmap_face_coverage_generic.py",
            "report_gate_a_partfield_vmap_quality_generic.py",
        ):
            write(scripts / name, (source_scripts / name).read_text())

        partfield = root / "PartField"
        write(partfield / "configs/final/demo.yaml", "test: true\n")
        write(partfield / "model/model_objaverse.ckpt", "checkpoint")
        inference = r'''import argparse
from pathlib import Path
import numpy as np
import trimesh
p=argparse.ArgumentParser(); p.add_argument('-c'); p.add_argument('--opts',nargs='+'); a=p.parse_args()
opts=a.opts; values={opts[i]:opts[i+1] for i in range(0,len(opts),2)}
out=Path(__file__).parent/'exp_results'/values['result_name']; out.mkdir(parents=True,exist_ok=True)
source=trimesh.load(Path(values['dataset.data_path'])/'00000.obj',force='mesh',process=False)
source.export(out/'input_00000_0.ply')
np.save(out/'part_feat_00000_0_batch.npy',np.ones((len(source.faces),4)))
'''
        clustering = r'''import argparse
from pathlib import Path
import numpy as np
import trimesh
p=argparse.ArgumentParser(); p.add_argument('--root'); p.add_argument('--dump_dir'); p.add_argument('--source_dir'); p.add_argument('--use_agglo'); p.add_argument('--max_num_clusters'); p.add_argument('--option'); a=p.parse_args()
out=Path(a.dump_dir); (out/'cluster_out').mkdir(parents=True,exist_ok=True); (out/'ply').mkdir(parents=True,exist_ok=True)
mesh=trimesh.load(Path(a.source_dir)/'00000.obj',force='mesh',process=False)
labels=np.full(len(mesh.faces),10,dtype=np.int64); labels[:48]=20
np.save(out/'cluster_out'/'00000_0_02.npy',labels)
mesh.export(out/'ply'/'00000_0_02.ply')
'''
        write(partfield / "partfield_inference.py", inference)
        write(partfield / "run_part_clustering.py", clustering)

        base = trimesh.creation.box(extents=(2.0, 1.0, 0.2)).subdivide()
        screen = trimesh.creation.box(extents=(2.0, 0.2, 1.4))
        screen.apply_translation((0.0, 0.4, 0.8))
        object_mesh = root / "object.ply"
        trimesh.util.concatenate([base, screen]).export(object_mesh)
        q0 = write(root / "q0.json", "{}\n")

        evidence = {}
        for role in ("panel", "get_hunyuan_input", "inpaint", "moge", "hunyuan", "hamer", "h2m", "mano_registration"):
            owner = write(root / f"{role}.bin", role)
            evidence[role] = {"path": str(owner), "sha256": gate_a.sha(owner)}
        q1_result = write(root / "q1.json", json.dumps({"decoded": {"overall_decision": "PASS"}}))
        foundation = root / "foundation.json"
        foundation.write_text(json.dumps({
            "schema": "tracehoi.FoundationTerminalPass.v1", "case_id": "alapuse02v3n60",
            "source_round": "Q1", "source_result": str(q1_result),
            "source_result_sha256": gate_a.sha(q1_result), "Q2_calls_in_lineage": 0,
            "decision": "foundation_terminal_pass_closed", "eligible_for_gate_a": True,
            "errors": [], "evidence": evidence,
        }))
        config = root / "gate_a.json"
        config.write_text(json.dumps({
            "schema": "tracehoi.GateAConfig.v1", "case_id": "alapuse02v3n60",
            "project_root": str(project), "partfield_root": str(partfield),
            "partfield_python_env": "FOHO_PARTFIELD_PYTHON",
            "partfield_config": "configs/final/demo.yaml", "checkpoint": "model/model_objaverse.ckpt",
            "result_name": "fake_gate_a", "q0": {"path": str(q0), "sha256": gate_a.sha(q0)},
            "object_mesh": {"path": str(object_mesh), "sha256": gate_a.sha(object_mesh)},
            "scripts": {
                "merge": str(scripts / "run_gate_a_partfield_vmap_merge_adapter.py"),
                "coverage": str(scripts / "check_gate_a_partfield_vmap_face_coverage_generic.py"),
                "quality": str(scripts / "report_gate_a_partfield_vmap_quality_generic.py"),
            },
            "target_faces": 30000, "n_point_per_face": 1, "n_sample_each": 10000,
            "max_num_clusters": 2, "cluster_option": 0,
            "expected_parts": ["screen_lid", "keyboard_base"],
            "semantic_mapping_policy": "alapuse02v3n60_n2_face_count_v1",
            "timeouts": {"partfield_seconds": 60, "cpu_step_seconds": 60},
            "thresholds": {"minimum_unique_face_coverage": 0.95, "maximum_duplicate_ratio": 0.05,
                           "minimum_bbox_ratio": 0.90, "maximum_bbox_ratio": 1.10},
        }))
        owners = {}
        for role in ("combined_q0", "gate_a", "gate_c_auto_v2", "gate_d0", "f0"):
            owner = write(root / f"owner_{role}.txt", role)
            owners[role] = {"terminal_validator_required": True,
                            "records": [{"locator": str(owner), "sha256": gate_a.sha(owner)}]}
        bundle = root / "bundle.json"
        bundle.write_text(json.dumps({"schema": "tracehoi.AutomaticSemanticOwnerBundles.v1",
                                      "decision": "automatic_semantic_owner_bundles_closed_for_mocking",
                                      "owners": owners}))
        post_config = root / "post.json"
        post_config.write_text(json.dumps({"schema": "tracehoi.PostQ2Config.v1", "case_id": "alapuse02v3n60",
                                           "owner_bundle": str(bundle), "roots": {},
                                           "stage_order": list(post.STAGES)}))
        return config, foundation, q0, post_config

    def test_plan_starts_no_child_and_owns_exact_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            config, foundation, _, _ = self.fixture(Path(temp))
            packet = gate_a.plan(config, foundation, Path(temp) / "run")
            self.assertEqual(packet["decision"], "real_gate_A_plan_closed")
            self.assertEqual(packet["child_processes_started"], 0)
            self.assertEqual(packet["cuda_steps"], ["partfield"])
            self.assertIn("partfield_inference.py", " ".join(packet["commands"]["partfield"]))
            self.assertIn("run_part_clustering.py", " ".join(packet["commands"]["cluster"]))

    def test_stale_q0_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            config, foundation, q0, _ = self.fixture(Path(temp))
            q0.write_text("changed")
            with self.assertRaises(gate_a.GateAAdapterError):
                gate_a.plan(config, foundation, Path(temp) / "run")

    def test_fake_runtime_handoff_and_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); config, foundation, _, post_config = self.fixture(root)
            previous = os.environ.get("FOHO_PARTFIELD_PYTHON")
            os.environ["FOHO_PARTFIELD_PYTHON"] = sys.executable
            try:
                state = post.run_real_gate_a(post_config, config, foundation, root / "post_run")
                self.assertEqual(state["next_index"], 1)
                self.assertEqual(state["history"][0]["stage"], "gate_a")
                gate_root = root / "post_run/00_gate_a/gate_a_runtime"
                audit = gate_a.audit(config, foundation, gate_root)
                self.assertEqual(audit["decision"], "real_gate_A_audit_closed")
                resumed = post.run_real_gate_a(post_config, config, foundation, root / "post_run")
                self.assertEqual(resumed["next_index"], 1)
            finally:
                if previous is None:
                    os.environ.pop("FOHO_PARTFIELD_PYTHON", None)
                else:
                    os.environ["FOHO_PARTFIELD_PYTHON"] = previous


if __name__ == "__main__":
    unittest.main(verbosity=2)
