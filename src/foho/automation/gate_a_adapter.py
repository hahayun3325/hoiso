from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping

from foho.automation.foundation_terminal_contract import validate_foundation_terminal


class GateAAdapterError(RuntimeError):
    pass


STEPS = ("prepare", "partfield", "cluster", "split", "semantic_merge", "audit")


def sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _atomic_json(path: Path, packet: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(packet), indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def _load_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file():
        raise GateAAdapterError(f"missing JSON owner: {source}")
    try:
        packet = json.loads(source.read_text())
    except Exception as exc:
        raise GateAAdapterError(f"invalid JSON owner: {source}") from exc
    if not isinstance(packet, dict):
        raise GateAAdapterError(f"JSON owner is not an object: {source}")
    return packet


def _require_hash(record: Mapping[str, Any], role: str) -> Path:
    path = Path(str(record.get("path", "")))
    if not path.is_file():
        raise GateAAdapterError(f"missing {role}: {path}")
    if sha(path) != record.get("sha256"):
        raise GateAAdapterError(f"stale {role}: {path}")
    return path


def load_config(path: str | Path) -> dict[str, Any]:
    config = _load_json(path)
    if config.get("schema") != "tracehoi.GateAConfig.v1":
        raise GateAAdapterError("Gate-A config schema")
    if config.get("case_id") != "alapuse02v3n60":
        raise GateAAdapterError("Gate-A case identity")
    if config.get("expected_parts") != ["screen_lid", "keyboard_base"]:
        raise GateAAdapterError("Gate-A semantic part order")
    if int(config.get("target_faces", 0)) != 30000:
        raise GateAAdapterError("Gate-A target face count")
    if int(config.get("n_point_per_face", 0)) != 1:
        raise GateAAdapterError("Gate-A n_point_per_face")
    if int(config.get("n_sample_each", 0)) != 10000:
        raise GateAAdapterError("Gate-A n_sample_each")
    if int(config.get("max_num_clusters", 0)) != 2:
        raise GateAAdapterError("Gate-A N=2 policy")
    if config.get("semantic_mapping_policy") != "alapuse02v3n60_n2_face_count_v1":
        raise GateAAdapterError("Gate-A semantic mapping policy")
    if int(config.get("timeouts", {}).get("partfield_seconds", 0)) <= 0:
        raise GateAAdapterError("Gate-A PartField timeout")
    if int(config.get("timeouts", {}).get("cpu_step_seconds", 0)) <= 0:
        raise GateAAdapterError("Gate-A CPU timeout")
    return config


def _runtime_python(config: Mapping[str, Any]) -> str:
    variable = str(config.get("partfield_python_env", "FOHO_PARTFIELD_PYTHON"))
    value = os.environ.get(variable) or sys.executable
    path = Path(value)
    if not path.is_file():
        raise GateAAdapterError(f"PartField Python is absent: {value}")
    return str(path.resolve())


def _owners(config: Mapping[str, Any], foundation_result: str | Path) -> dict[str, Any]:
    accepted = validate_foundation_terminal(foundation_result)
    if accepted.get("case_id") != config["case_id"]:
        raise GateAAdapterError("foundation terminal case mismatch")
    q0 = _require_hash(config["q0"], "accepted Q0")
    object_mesh = _require_hash(config["object_mesh"], "accepted object mesh")
    root = Path(config["partfield_root"])
    if not root.is_dir():
        raise GateAAdapterError(f"PartField root is absent: {root}")
    required = {
        "inference": root / "partfield_inference.py",
        "clustering": root / "run_part_clustering.py",
        "partfield_config": root / config["partfield_config"],
        "checkpoint": root / config["checkpoint"],
    }
    for role, path in config["scripts"].items():
        required[role] = Path(path)
    for role, path in required.items():
        if not path.is_file():
            raise GateAAdapterError(f"missing runtime owner {role}: {path}")
    return {
        "acceptance": accepted,
        "q0": q0,
        "object_mesh": object_mesh,
        "partfield_root": root,
        "required": required,
        "python": _runtime_python(config),
    }


def _paths(config: Mapping[str, Any], run_root: str | Path) -> dict[str, Path]:
    root = Path(run_root).resolve()
    run_fingerprint = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:12]
    run_name = f"{config['result_name']}_{root.name}_{run_fingerprint}"
    partfield = root / "partfield"
    return {
        "root": root,
        "state": root / "state.json",
        "receipts": root / "receipts",
        "failures": root / "failures",
        "logs": root / "logs",
        "input_dir": partfield / "input_mesh_low30k",
        "input_mesh": partfield / "input_mesh_low30k" / "00000.obj",
        "feature_dir": Path(config["partfield_root"]) / "exp_results" / "partfield_features" / run_name,
        "cluster_dir": partfield / "clustering_n2",
        "cluster_labels": partfield / "clustering_n2" / "cluster_out" / "00000_0_02.npy",
        "part_dir": partfield / "partseps_low30k",
        "semantic_dir": root / "artifacts" / "semantic_parts",
        "merge_json": root / "reports" / "semantic_merge.json",
        "coverage": root / "reports" / "face_coverage.json",
        "quality": root / "reports" / "part_quality.json",
        "hinge": root / "reports" / "hinge_metadata.json",
        "whole": root / "artifacts" / "whole_object.ply",
        "terminal": root / "gate_a_terminal.json",
    }


def _commands(config: Mapping[str, Any], owners: Mapping[str, Any], paths: Mapping[str, Path]) -> dict[str, list[str]]:
    py = owners["python"]
    required = owners["required"]
    root = owners["partfield_root"]
    return {
        "partfield": [
            py, str(required["inference"]), "-c", str(required["partfield_config"]),
            "--opts", "continue_ckpt", str(required["checkpoint"]),
            "result_name", f"partfield_features/{paths['feature_dir'].name}",
            "dataset.data_path", str(paths["input_dir"]),
            "n_point_per_face", str(config["n_point_per_face"]),
            "n_sample_each", str(config["n_sample_each"]),
        ],
        "cluster": [
            py, str(required["clustering"]), "--root", str(paths["feature_dir"]),
            "--dump_dir", str(paths["cluster_dir"]), "--source_dir", str(paths["input_dir"]),
            "--use_agglo", "True", "--max_num_clusters", str(config["max_num_clusters"]),
            "--option", str(config["cluster_option"]),
        ],
        "split": ["internal", "split_partfield_face_labels_v1"],
        "merge": [
            sys.executable, str(required["merge"]), "--case", config["case_id"],
            "--source-mesh", str(paths["input_mesh"]), "--pfsep", str(paths["part_dir"]),
            "--merge-json", str(paths["merge_json"]), "--out-dir", str(paths["semantic_dir"]),
        ],
        "coverage": [
            sys.executable, str(required["coverage"]), "--case-root", str(paths["root"]),
            "--merge-json", str(paths["merge_json"]), "--out", str(paths["coverage"]),
        ],
        "quality": [
            sys.executable, str(required["quality"]), "--case-root", str(paths["root"]),
            "--part-dir", str(paths["semantic_dir"]), "--out", str(paths["quality"]),
        ],
    }


def plan(config_path: str | Path, foundation_result: str | Path, run_root: str | Path) -> dict[str, Any]:
    config = load_config(config_path)
    owners = _owners(config, foundation_result)
    paths = _paths(config, run_root)
    commands = _commands(config, owners, paths)
    return {
        "schema": "tracehoi.GateAPlan.v1",
        "case_id": config["case_id"],
        "foundation_terminal": owners["acceptance"],
        "q0": {"path": str(owners["q0"]), "sha256": sha(owners["q0"])},
        "object_mesh": {"path": str(owners["object_mesh"]), "sha256": sha(owners["object_mesh"])},
        "partfield_root": str(owners["partfield_root"]),
        "partfield_python": owners["python"],
        "steps": list(STEPS),
        "commands": commands,
        "cuda_steps": ["partfield"],
        "api_calls": 0,
        "child_processes_started": 0,
        "decision": "real_gate_A_plan_closed",
    }


def _prepare_mesh(source: Path, target: Path, whole: Path, target_faces: int) -> dict[str, Any]:
    import numpy as np
    import trimesh

    mesh = trimesh.load(source, force="mesh", process=False)
    if len(mesh.vertices) == 0 or len(mesh.faces) == 0:
        raise GateAAdapterError("accepted object mesh is empty")
    if not np.isfinite(mesh.vertices).all():
        raise GateAAdapterError("accepted object mesh is non-finite")
    original_faces = int(len(mesh.faces))
    prepared = mesh
    if original_faces > target_faces:
        try:
            prepared = mesh.simplify_quadric_decimation(face_count=target_faces)
        except TypeError:
            prepared = mesh.simplify_quadric_decimation(target_faces)
        except AttributeError as exc:
            raise GateAAdapterError("trimesh decimation backend is unavailable") from exc
    if len(prepared.faces) > target_faces or len(prepared.faces) == 0:
        raise GateAAdapterError("prepared mesh face count is invalid")
    target.parent.mkdir(parents=True, exist_ok=True)
    whole.parent.mkdir(parents=True, exist_ok=True)
    prepared.export(target)
    mesh.export(whole)
    return {
        "source_faces": original_faces,
        "prepared_faces": int(len(prepared.faces)),
        "prepared_vertices": int(len(prepared.vertices)),
        "input_mesh": str(target),
        "whole_object": str(whole),
    }


def _run_command(name: str, command: list[str], cwd: Path, log: Path, cuda: bool = False,
                 timeout_seconds: int | None = None) -> dict[str, Any]:
    log.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    if not cuda:
        env["CUDA_VISIBLE_DEVICES"] = ""
    started = time.time()
    with log.open("w") as stream:
        completed = subprocess.run(
            command, cwd=str(cwd), env=env, stdout=stream, stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
        )
    record = {
        "name": name,
        "command": command,
        "cwd": str(cwd),
        "returncode": int(completed.returncode),
        "elapsed_seconds": float(time.time() - started),
        "timeout_seconds": timeout_seconds,
        "log": str(log),
        "cuda_allowed": bool(cuda),
    }
    if completed.returncode != 0:
        raise GateAAdapterError(f"{name} returncode {completed.returncode}; inspect {log}")
    return record


def _output_records(paths: list[Path]) -> dict[str, dict[str, str]]:
    records = {}
    for path in paths:
        if not path.is_file():
            raise GateAAdapterError(f"expected output is absent: {path}")
        records[path.name] = {"path": str(path.resolve()), "sha256": sha(path)}
    return records


def _semantic_mapping(paths: Mapping[str, Path], config: Mapping[str, Any]) -> dict[str, Any]:
    import numpy as np
    import trimesh
    from scipy.spatial import cKDTree

    part_files = sorted(paths["part_dir"].glob("00000_part_*.ply"))
    part_files = [path for path in part_files if "_vmap" not in path.name]
    if len(part_files) != 2:
        raise GateAAdapterError(f"N=2 produced {len(part_files)} mesh parts")
    rows = []
    for path in part_files:
        mesh = trimesh.load(path, force="mesh", process=False)
        if len(mesh.faces) == 0 or not np.isfinite(mesh.vertices).all():
            raise GateAAdapterError(f"invalid cluster mesh: {path}")
        cluster_id = int(path.stem.rsplit("_", 1)[-1])
        rows.append({"cluster_id": cluster_id, "faces": int(len(mesh.faces)), "mesh": mesh})
    rows.sort(key=lambda row: row["faces"])
    if rows[0]["faces"] == rows[1]["faces"]:
        raise GateAAdapterError("case-specific face-count semantic rule is tied")
    screen, base = rows[0], rows[1]
    merge = {
        "schema": "tracehoi.GateASemanticMerge.v1",
        "case": config["case_id"],
        "policy": config["semantic_mapping_policy"],
        "physical_parts": {
            "screen_lid": [screen["cluster_id"]],
            "keyboard_base": [base["cluster_id"]],
        },
        "historical_oracle_used_as_output": False,
    }
    _atomic_json(paths["merge_json"], merge)
    screen_vertices = np.asarray(screen["mesh"].vertices)
    base_vertices = np.asarray(base["mesh"].vertices)
    tree = cKDTree(base_vertices)
    distances, indices = tree.query(screen_vertices, k=1)
    count = max(8, min(len(screen_vertices), int(round(0.02 * len(screen_vertices)))))
    chosen = np.argsort(distances)[:count]
    boundary = 0.5 * (screen_vertices[chosen] + base_vertices[indices[chosen]])
    center = boundary.mean(axis=0)
    _, _, vh = np.linalg.svd(boundary - center, full_matrices=False)
    direction = vh[0] / max(np.linalg.norm(vh[0]), 1e-12)
    hinge = {
        "schema": "tracehoi.GateAHingeMetadata.v1",
        "source": "nearest-boundary PCA between fresh N=2 semantic parts",
        "independent_partfield_cluster": False,
        "point_xyz": center.tolist(),
        "direction_xyz": direction.tolist(),
        "boundary_samples": int(len(boundary)),
        "median_cross_part_distance": float(np.median(distances[chosen])),
    }
    _atomic_json(paths["hinge"], hinge)
    return {"merge": merge, "hinge": hinge}


def _split_parts(source_mesh: Path, cluster_labels: Path, out_dir: Path) -> dict[str, Any]:
    import numpy as np
    import trimesh

    mesh = trimesh.load(source_mesh, force="mesh", process=False)
    labels = np.load(cluster_labels, allow_pickle=True).reshape(-1)
    if len(labels) != len(mesh.faces):
        raise GateAAdapterError(
            f"cluster labels are not per-face: labels={len(labels)} faces={len(mesh.faces)}"
        )
    unique = sorted(int(value) for value in np.unique(labels))
    if len(unique) != 2:
        raise GateAAdapterError(f"N=2 labels contain {len(unique)} unique values")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for cluster_id in unique:
        face_ids = np.where(labels == cluster_id)[0]
        vertex_ids = np.unique(mesh.faces[face_ids].reshape(-1))
        part = mesh.submesh([face_ids], append=True, repair=False)
        part_path = out_dir / f"00000_part_{cluster_id}.ply"
        vmap_path = out_dir / f"00000_part_{cluster_id}_vmap.npy"
        part.export(part_path)
        np.save(vmap_path, vertex_ids)
        rows.append({
            "cluster_id": cluster_id, "faces": int(len(face_ids)),
            "vertices": int(len(vertex_ids)), "mesh": str(part_path), "vmap": str(vmap_path),
        })
    return {"policy": "per-face labels", "clusters": rows}


def _audit_outputs(paths: Mapping[str, Path], config: Mapping[str, Any], foundation_result: Path) -> dict[str, Any]:
    import numpy as np
    import trimesh

    coverage = _load_json(paths["coverage"])
    quality = _load_json(paths["quality"])
    merge = _load_json(paths["merge_json"])
    hinge = _load_json(paths["hinge"])
    manifest = _load_json(paths["semantic_dir"] / "part_manifest.json")
    errors = []
    expected = set(config["expected_parts"])
    if set(manifest.get("parts", {})) != expected:
        errors.append("semantic_part_set")
    part_records = {}
    for name in config["expected_parts"]:
        path = paths["semantic_dir"] / f"{name}.ply"
        if not path.is_file():
            errors.append(f"missing_part:{name}")
            continue
        mesh = trimesh.load(path, force="mesh", process=False)
        components = mesh.split(only_watertight=False)
        if len(mesh.faces) == 0 or not np.isfinite(mesh.vertices).all():
            errors.append(f"invalid_part:{name}")
        part_records[name] = {
            "path": str(path.resolve()), "sha256": sha(path),
            "vertices": int(len(mesh.vertices)), "faces": int(len(mesh.faces)),
            "connected_components": int(len(components)),
        }
    thresholds = config["thresholds"]
    coverage_ratio = float(coverage.get("unique_face_coverage_ratio", -1.0))
    duplicate_ratio = float(coverage.get("duplicate_ratio_over_selected", 1.0))
    bbox_ratio = np.asarray(quality.get("bbox_size_ratio", []), dtype=float)
    if coverage_ratio < float(thresholds["minimum_unique_face_coverage"]):
        errors.append(f"coverage:{coverage_ratio}")
    if duplicate_ratio > float(thresholds["maximum_duplicate_ratio"]):
        errors.append(f"duplicate_ratio:{duplicate_ratio}")
    if bbox_ratio.shape != (3,) or not np.isfinite(bbox_ratio).all():
        errors.append("bbox_ratio")
    else:
        low = float(thresholds["minimum_bbox_ratio"])
        high = float(thresholds["maximum_bbox_ratio"])
        if np.any(bbox_ratio < low) or np.any(bbox_ratio > high):
            errors.append(f"bbox_ratio:{bbox_ratio.tolist()}")
    if errors:
        raise GateAAdapterError("Gate-A output audit: " + ",".join(errors))
    return {
        "schema": "tracehoi.GateATerminalReceipt.v1",
        "case_id": config["case_id"],
        "decision": "real_gate_A_terminal_closed",
        "eligible_for_frame_i": True,
        "foundation_terminal": {"path": str(foundation_result.resolve()), "sha256": sha(foundation_result)},
        "whole_object": {"path": str(paths["whole"].resolve()), "sha256": sha(paths["whole"])},
        "parts": part_records,
        "semantic_merge": {"path": str(paths["merge_json"].resolve()), "sha256": sha(paths["merge_json"]), "packet": merge},
        "hinge": {"path": str(paths["hinge"].resolve()), "sha256": sha(paths["hinge"]), "packet": hinge},
        "coverage": {"path": str(paths["coverage"].resolve()), "sha256": sha(paths["coverage"]), "packet": coverage},
        "quality": {"path": str(paths["quality"].resolve()), "sha256": sha(paths["quality"]), "packet": quality},
        "historical_output_promoted": False,
        "api_calls": 0,
        "errors": [],
    }


def _valid_receipt(receipt: Mapping[str, Any]) -> bool:
    outputs = receipt.get("outputs", {})
    if not isinstance(outputs, dict) or not outputs:
        return False
    for record in outputs.values():
        path = Path(str(record.get("path", "")))
        if not path.is_file() or sha(path) != record.get("sha256"):
            return False
    return True


def _record_step(paths: Mapping[str, Path], state: dict[str, Any], step: str, outputs: list[Path], detail: Mapping[str, Any]) -> None:
    records = _output_records(outputs)
    receipt = {
        "schema": "tracehoi.GateAStepReceipt.v1",
        "case_id": state["case_id"], "step": step,
        "outputs": records, "detail": dict(detail), "decision": f"gate_A_{step}_closed",
    }
    index = STEPS.index(step)
    receipt_path = paths["receipts"] / f"{index:02d}_{step}.json"
    _atomic_json(receipt_path, receipt)
    state["completed_steps"].append({"step": step, "receipt": str(receipt_path), "sha256": sha(receipt_path)})
    state["next_index"] = index + 1
    state["status"] = "ready"
    _atomic_json(paths["state"], state)


def run(config_path: str | Path, foundation_result: str | Path, run_root: str | Path) -> dict[str, Any]:
    config = load_config(config_path)
    foundation_result = Path(foundation_result).resolve()
    owners = _owners(config, foundation_result)
    paths = _paths(config, run_root)
    commands = _commands(config, owners, paths)
    paths["root"].mkdir(parents=True, exist_ok=True)
    identity = {
        "foundation_terminal_sha256": sha(foundation_result),
        "q0_sha256": sha(owners["q0"]),
        "object_mesh_sha256": sha(owners["object_mesh"]),
        "config_sha256": sha(config_path),
    }
    if paths["state"].is_file():
        state = _load_json(paths["state"])
        if state.get("identity") != identity:
            raise GateAAdapterError("Gate-A resume identity mismatch")
    else:
        state = {
            "schema": "tracehoi.GateAState.v1", "case_id": config["case_id"],
            "steps": list(STEPS), "next_index": 0, "completed_steps": [],
            "status": "ready", "identity": identity, "api_calls": 0,
        }
        _atomic_json(paths["state"], state)
    for closed in state["completed_steps"]:
        receipt_path = Path(closed["receipt"])
        if not receipt_path.is_file() or sha(receipt_path) != closed["sha256"] or not _valid_receipt(_load_json(receipt_path)):
            raise GateAAdapterError(f"stale completed step: {closed['step']}")
    while int(state["next_index"]) < len(STEPS):
        step = STEPS[int(state["next_index"])]
        try:
            if step == "prepare":
                detail = _prepare_mesh(owners["object_mesh"], paths["input_mesh"], paths["whole"], int(config["target_faces"]))
                outputs = [paths["input_mesh"], paths["whole"]]
            elif step == "partfield":
                detail = _run_command(
                    step, commands[step], owners["partfield_root"], paths["logs"] / "partfield.log",
                    cuda=True, timeout_seconds=int(config["timeouts"]["partfield_seconds"]),
                )
                outputs = [paths["feature_dir"] / "part_feat_00000_0_batch.npy", paths["feature_dir"] / "input_00000_0.ply"]
            elif step == "cluster":
                detail = _run_command(
                    step, commands[step], owners["partfield_root"], paths["logs"] / "cluster.log",
                    timeout_seconds=int(config["timeouts"]["cpu_step_seconds"]),
                )
                outputs = [paths["cluster_labels"]]
            elif step == "split":
                detail = _split_parts(paths["input_mesh"], paths["cluster_labels"], paths["part_dir"])
                outputs = sorted(paths["part_dir"].glob("00000_part_*"))
            elif step == "semantic_merge":
                detail = _semantic_mapping(paths, config)
                merge_run = _run_command(
                    "merge", commands["merge"], Path(config["project_root"]), paths["logs"] / "merge.log",
                    timeout_seconds=int(config["timeouts"]["cpu_step_seconds"]),
                )
                detail["command"] = merge_run
                outputs = [paths["merge_json"], paths["hinge"], paths["semantic_dir"] / "part_manifest.json", paths["semantic_dir"] / "screen_lid.ply", paths["semantic_dir"] / "keyboard_base.ply"]
            else:
                coverage_run = _run_command(
                    "coverage", commands["coverage"], Path(config["project_root"]), paths["logs"] / "coverage.log",
                    timeout_seconds=int(config["timeouts"]["cpu_step_seconds"]),
                )
                quality_run = _run_command(
                    "quality", commands["quality"], Path(config["project_root"]), paths["logs"] / "quality.log",
                    timeout_seconds=int(config["timeouts"]["cpu_step_seconds"]),
                )
                terminal = _audit_outputs(paths, config, foundation_result)
                _atomic_json(paths["terminal"], terminal)
                detail = {"coverage_command": coverage_run, "quality_command": quality_run}
                outputs = [paths["coverage"], paths["quality"], paths["terminal"]]
            _record_step(paths, state, step, outputs, detail)
            state = _load_json(paths["state"])
        except Exception as exc:
            failure = {
                "schema": "tracehoi.GateAStepFailure.v1", "case_id": config["case_id"],
                "step": step, "error_type": type(exc).__name__, "error": str(exc),
                "decision": "gate_A_failed_without_promotion",
            }
            _atomic_json(paths["failures"] / f"{step}.json", failure)
            state["status"] = "failed"
            state["failed_step"] = step
            _atomic_json(paths["state"], state)
            raise
    state["status"] = "complete"
    state.pop("failed_step", None)
    state["terminal_receipt"] = str(paths["terminal"])
    state["terminal_receipt_sha256"] = sha(paths["terminal"])
    _atomic_json(paths["state"], state)
    return _load_json(paths["terminal"])


def status(config_path: str | Path, run_root: str | Path) -> dict[str, Any]:
    load_config(config_path)
    path = _paths(load_config(config_path), run_root)["state"]
    if not path.is_file():
        raise GateAAdapterError("Gate-A state is absent")
    return _load_json(path)


def audit(config_path: str | Path, foundation_result: str | Path, run_root: str | Path) -> dict[str, Any]:
    config = load_config(config_path)
    _owners(config, foundation_result)
    paths = _paths(config, run_root)
    terminal = _load_json(paths["terminal"])
    if terminal.get("schema") != "tracehoi.GateATerminalReceipt.v1" or terminal.get("decision") != "real_gate_A_terminal_closed" or terminal.get("eligible_for_frame_i") is not True:
        raise GateAAdapterError("Gate-A terminal contract")
    for role in ("whole_object", "semantic_merge", "hinge", "coverage", "quality"):
        _require_hash(terminal[role], f"terminal {role}")
    for name in config["expected_parts"]:
        _require_hash(terminal["parts"][name], f"terminal part {name}")
    return {
        "schema": "tracehoi.GateAAudit.v1", "case_id": config["case_id"],
        "terminal_receipt": str(paths["terminal"]), "terminal_receipt_sha256": sha(paths["terminal"]),
        "eligible_for_frame_i": True, "decision": "real_gate_A_audit_closed",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("plan", "run", "resume", "status", "audit"))
    parser.add_argument("--config", required=True)
    parser.add_argument("--foundation-pass")
    parser.add_argument("--q2-result")
    parser.add_argument("--run-root", required=True)
    args = parser.parse_args()
    supplied = [value for value in (args.foundation_pass, args.q2_result) if value]
    if args.mode == "status":
        result = status(args.config, args.run_root)
    else:
        if len(supplied) != 1:
            raise GateAAdapterError("supply exactly one foundation terminal result")
        if args.mode == "plan":
            result = plan(args.config, supplied[0], args.run_root)
        elif args.mode == "audit":
            result = audit(args.config, supplied[0], args.run_root)
        else:
            result = run(args.config, supplied[0], args.run_root)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
