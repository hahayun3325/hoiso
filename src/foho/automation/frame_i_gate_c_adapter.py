from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import trimesh
from scipy.spatial import cKDTree


class FrameIGateCError(RuntimeError):
    pass


def sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path: Path, packet: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(packet), indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def load_json(path: str | Path, schema: str | None = None) -> dict[str, Any]:
    packet = json.loads(Path(path).read_text())
    if schema is not None and packet.get("schema") != schema:
        raise FrameIGateCError(f"schema:{path}:{packet.get('schema')}!= {schema}")
    return packet


def checked_record(record: Mapping[str, Any], role: str) -> Path:
    path = Path(str(record.get("path", "")))
    expected = str(record.get("sha256", ""))
    if not path.is_file():
        raise FrameIGateCError(f"absent:{role}:{path}")
    if not expected or sha(path) != expected:
        raise FrameIGateCError(f"hash:{role}:{path}")
    return path


def load_mesh(path: str | Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if not isinstance(mesh, trimesh.Trimesh):
        raise FrameIGateCError(f"not_mesh:{path}")
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    if len(vertices) < 4 or len(faces) < 1 or not np.isfinite(vertices).all():
        raise FrameIGateCError(f"invalid_mesh:{path}")
    return mesh


def sample_surface(mesh: trimesh.Trimesh, count: int, seed: int) -> np.ndarray:
    state = np.random.get_state()
    np.random.seed(seed)
    try:
        points, _ = trimesh.sample.sample_surface(mesh, count)
    finally:
        np.random.set_state(state)
    return np.asarray(points, dtype=np.float64)


def umeyama_similarity(source: np.ndarray, target: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    if source.shape != target.shape or source.ndim != 2 or source.shape[1] != 3:
        raise FrameIGateCError("similarity_shape")
    source_mean = source.mean(axis=0)
    target_mean = target.mean(axis=0)
    source_zero = source - source_mean
    target_zero = target - target_mean
    covariance = (target_zero.T @ source_zero) / len(source)
    left, singular, right_t = np.linalg.svd(covariance)
    sign = np.ones(3)
    if np.linalg.det(left @ right_t) < 0:
        sign[-1] = -1
    rotation = left @ np.diag(sign) @ right_t
    variance = float(np.sum(source_zero * source_zero) / len(source))
    if variance <= 1e-18:
        raise FrameIGateCError("degenerate_similarity")
    scale = float(np.sum(singular * sign) / variance)
    translation = target_mean - scale * (rotation @ source_mean)
    return scale, rotation, translation


def matrix_from_similarity(scale: float, rotation: np.ndarray, translation: np.ndarray) -> np.ndarray:
    matrix = np.eye(4, dtype=np.float64)
    matrix[:3, :3] = scale * rotation
    matrix[:3, 3] = translation
    return matrix


def apply_matrix(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    return points @ matrix[:3, :3].T + matrix[:3, 3]


def transform_mesh(mesh: trimesh.Trimesh, matrix: np.ndarray) -> trimesh.Trimesh:
    output = mesh.copy()
    output.apply_transform(matrix)
    return output


def _pca_rotations(source: np.ndarray, target: np.ndarray) -> list[np.ndarray]:
    source_zero = source - source.mean(axis=0)
    target_zero = target - target.mean(axis=0)
    _, source_basis = np.linalg.eigh(source_zero.T @ source_zero / len(source))
    _, target_basis = np.linalg.eigh(target_zero.T @ target_zero / len(target))
    source_basis = source_basis[:, ::-1]
    target_basis = target_basis[:, ::-1]
    rotations = [np.eye(3)]
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                rotation = target_basis @ np.diag([sx, sy, sz]) @ source_basis.T
                if np.linalg.det(rotation) > 0:
                    rotations.append(rotation)
    return rotations


def _registration_metrics(source: np.ndarray, target: np.ndarray, matrix: np.ndarray) -> dict[str, float]:
    transformed = apply_matrix(source, matrix)
    forward = cKDTree(target).query(transformed, k=1)[0]
    backward = cKDTree(transformed).query(target, k=1)[0]
    combined = np.concatenate((forward, backward))
    diagonal = float(np.linalg.norm(np.ptp(target, axis=0)))
    if diagonal <= 1e-12:
        raise FrameIGateCError("degenerate_reference_extent")
    return {
        "reference_diagonal": diagonal,
        "symmetric_mean": float(combined.mean()),
        "symmetric_p95": float(np.quantile(combined, 0.95)),
        "normalized_symmetric_mean": float(combined.mean() / diagonal),
        "normalized_symmetric_p95": float(np.quantile(combined, 0.95) / diagonal),
    }


def estimate_similarity(
    source_mesh: trimesh.Trimesh,
    target_mesh: trimesh.Trimesh,
    policy: Mapping[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    source_vertices = np.asarray(source_mesh.vertices, dtype=np.float64)
    target_vertices = np.asarray(target_mesh.vertices, dtype=np.float64)
    candidates: list[tuple[str, np.ndarray, dict[str, float]]] = []
    correspondence_limit = float(policy["correspondence_normalized_mean_max"])
    if source_vertices.shape == target_vertices.shape:
        scale, rotation, translation = umeyama_similarity(source_vertices, target_vertices)
        matrix = matrix_from_similarity(scale, rotation, translation)
        metrics = _registration_metrics(source_vertices, target_vertices, matrix)
        if metrics["normalized_symmetric_mean"] <= correspondence_limit:
            candidates.append(("vertex_correspondence", matrix, metrics))

    count = int(policy["sample_count"])
    source = sample_surface(source_mesh, count, int(policy["seed"]))
    target = sample_surface(target_mesh, count, int(policy["seed"]) + 1)
    source_center = source.mean(axis=0)
    target_center = target.mean(axis=0)
    source_radius = math.sqrt(float(np.mean(np.sum((source - source_center) ** 2, axis=1))))
    target_radius = math.sqrt(float(np.mean(np.sum((target - target_center) ** 2, axis=1))))
    if source_radius <= 1e-12 or target_radius <= 1e-12:
        raise FrameIGateCError("degenerate_registration_input")
    initial_scale = target_radius / source_radius
    target_tree = cKDTree(target)
    keep_count = max(32, int(math.ceil(float(policy["trim_fraction"]) * len(source))))
    for initial_rotation in _pca_rotations(source, target):
        matrix = matrix_from_similarity(
            initial_scale,
            initial_rotation,
            target_center - initial_scale * (initial_rotation @ source_center),
        )
        previous = math.inf
        try:
            for _ in range(int(policy["max_iterations"])):
                current = apply_matrix(source, matrix)
                distances, indices = target_tree.query(current, k=1)
                keep = np.argpartition(distances, keep_count - 1)[:keep_count]
                if np.unique(indices[keep]).size < 4:
                    raise FrameIGateCError("degenerate_icp_correspondence")
                scale, rotation, translation = umeyama_similarity(current[keep], target[indices[keep]])
                matrix = matrix_from_similarity(scale, rotation, translation) @ matrix
                error = float(np.mean(np.partition(distances, keep_count - 1)[:keep_count]))
                if abs(previous - error) <= float(policy["tolerance"]):
                    break
                previous = error
            metrics = _registration_metrics(source, target, matrix)
            candidates.append(("pca_multistart_trimmed_icp", matrix, metrics))
        except (FrameIGateCError, ValueError, np.linalg.LinAlgError):
            continue
    if not candidates:
        raise FrameIGateCError("no_valid_similarity_candidate")
    method, matrix, metrics = min(candidates, key=lambda item: item[2]["normalized_symmetric_mean"])
    singular = np.linalg.svd(matrix[:3, :3], compute_uv=False)
    scale = float(singular.mean())
    determinant = float(np.linalg.det(matrix[:3, :3]))
    metrics.update(
        {
            "method": method,
            "scale": scale,
            "determinant": determinant,
            "similarity_singular_ratio": float(singular.max() / singular.min()),
            "candidate_count": len(candidates),
        }
    )
    errors = []
    if not np.isfinite(matrix).all():
        errors.append("nonfinite_transform")
    if determinant <= 0:
        errors.append("nonpositive_determinant")
    if not float(policy["scale_min"]) <= scale <= float(policy["scale_max"]):
        errors.append("scale_outside_policy")
    if metrics["similarity_singular_ratio"] > float(policy["similarity_singular_ratio_max"]):
        errors.append("not_similarity_transform")
    if metrics["normalized_symmetric_mean"] > float(policy["normalized_symmetric_mean_max"]):
        errors.append("mean_residual_outside_policy")
    if metrics["normalized_symmetric_p95"] > float(policy["normalized_symmetric_p95_max"]):
        errors.append("p95_residual_outside_policy")
    if errors:
        raise FrameIGateCError("registration_hold:" + ",".join(errors) + ":" + json.dumps(metrics, sort_keys=True))
    return matrix, metrics


def active_patch_face_ids(packet: Mapping[str, Any], part: str, region: str) -> np.ndarray:
    try:
        values = packet["parts"][part]["regions"][region]["face_ids"]
    except (KeyError, TypeError) as exc:
        raise FrameIGateCError(f"missing_patch_owner:{part}:{region}") from exc
    ids = np.unique(np.asarray(values, dtype=np.int64))
    if ids.ndim != 1 or len(ids) == 0:
        raise FrameIGateCError("empty_historical_patch")
    return ids


def selected_component_ratio(mesh: trimesh.Trimesh, selected_ids: np.ndarray) -> float:
    selected = set(int(value) for value in selected_ids)
    adjacency: dict[int, set[int]] = {value: set() for value in selected}
    for left, right in np.asarray(mesh.face_adjacency, dtype=np.int64):
        if int(left) in selected and int(right) in selected:
            adjacency[int(left)].add(int(right))
            adjacency[int(right)].add(int(left))
    seen: set[int] = set()
    largest = 0
    for start in selected:
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        size = 0
        while stack:
            node = stack.pop()
            size += 1
            for neighbor in adjacency[node]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        largest = max(largest, size)
    return float(largest / len(selected))


def remap_patch(
    reference_mesh: trimesh.Trimesh,
    fresh_screen_in_i: trimesh.Trimesh,
    old_ids: np.ndarray,
    policy: Mapping[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    if int(old_ids.min()) < 0 or int(old_ids.max()) >= len(reference_mesh.faces):
        raise FrameIGateCError("historical_patch_face_range")
    old_triangles = np.asarray(reference_mesh.triangles, dtype=np.float64)[old_ids]
    old_centers = old_triangles.mean(axis=1)
    fresh_centers = np.asarray(fresh_screen_in_i.triangles_center, dtype=np.float64)
    distances, mapped = cKDTree(fresh_centers).query(old_centers, k=1)
    fresh_ids = np.unique(np.asarray(mapped, dtype=np.int64))
    diagonal = float(np.linalg.norm(fresh_screen_in_i.extents))
    if diagonal <= 1e-12:
        raise FrameIGateCError("fresh_screen_extent")
    metrics = {
        "historical_face_count": int(len(old_ids)),
        "fresh_face_count": int(len(fresh_ids)),
        "fresh_screen_face_count": int(len(fresh_screen_in_i.faces)),
        "fresh_fraction": float(len(fresh_ids) / len(fresh_screen_in_i.faces)),
        "normalized_mapping_mean": float(np.mean(distances) / diagonal),
        "normalized_mapping_p95": float(np.quantile(distances, 0.95) / diagonal),
        "largest_component_ratio": selected_component_ratio(fresh_screen_in_i, fresh_ids),
    }
    errors = []
    if len(fresh_ids) < int(policy["min_faces"]):
        errors.append("patch_too_small")
    if len(fresh_ids) >= len(fresh_screen_in_i.faces):
        errors.append("patch_not_strict_subset")
    if metrics["fresh_fraction"] > float(policy["max_screen_fraction"]):
        errors.append("patch_too_broad")
    if metrics["normalized_mapping_p95"] > float(policy["normalized_mapping_p95_max"]):
        errors.append("patch_mapping_residual")
    if metrics["largest_component_ratio"] < float(policy["largest_component_ratio_min"]):
        errors.append("patch_disconnected")
    if errors:
        raise FrameIGateCError("patch_hold:" + ",".join(errors) + ":" + json.dumps(metrics, sort_keys=True))
    return fresh_ids, metrics


def run_frame_i(config_path: str | Path, output_root: str | Path) -> dict[str, Any]:
    config = load_json(config_path, "tracehoi.FreshFrameIGateCConfig.v1")
    root = Path(output_root)
    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    binding_path = checked_record(config["owners"]["binding_spec"], "binding_spec")
    binding = load_json(binding_path, "tracehoi.FreshGateAToFrameIGateCBindingSpec.v1")
    if binding.get("decision") != "fresh_gate_A_frame_I_gate_C_binding_spec_closed":
        raise FrameIGateCError("binding_not_closed")
    if binding.get("historical_face_ids_reused") is not False:
        raise FrameIGateCError("stale_face_id_boundary")
    fresh_records = {
        "whole_object": binding["fresh_whole_object"],
        "screen_lid": binding["fresh_part_owners"]["screen_lid"],
        "keyboard_base": binding["fresh_part_owners"]["keyboard_base"],
    }
    fresh_paths = {name: checked_record(record, f"fresh_{name}") for name, record in fresh_records.items()}
    reference_path = checked_record(binding["historical_reference_owners"]["frame_I_object_reference"], "frame_I_reference")
    patch_map_path = checked_record(binding["historical_reference_owners"]["historical_object_patch_map"], "historical_patch_map")
    source_hashes_before = {name: sha(path) for name, path in fresh_paths.items()}
    meshes = {name: load_mesh(path) for name, path in fresh_paths.items()}
    reference_mesh = load_mesh(reference_path)
    matrix, registration = estimate_similarity(meshes["whole_object"], reference_mesh, config["registration_policy"])
    transformed = {name: transform_mesh(mesh, matrix) for name, mesh in meshes.items()}
    output_paths: dict[str, Path] = {}
    for name, mesh in transformed.items():
        path = artifacts / f"fresh_{name}_in_I.ply"
        mesh.export(path)
        output_paths[name] = path
    transform_path = artifacts / "fresh_GateA_to_I_similarity.npy"
    np.save(transform_path, matrix)
    patch_packet = load_json(patch_map_path)
    part = str(config["semantic_contract"]["object_part"])
    region = str(config["semantic_contract"]["object_region_key"])
    old_ids = active_patch_face_ids(patch_packet, part, region)
    fresh_ids, patch_metrics = remap_patch(
        reference_mesh,
        transformed["screen_lid"],
        old_ids,
        config["patch_policy"],
    )
    face_ids_path = artifacts / "fresh_screen_lid_upper_left_top_rim_face_ids.npy"
    np.save(face_ids_path, fresh_ids)
    patch_mesh = transformed["screen_lid"].submesh([fresh_ids], append=True, repair=False)
    patch_mesh_path = artifacts / "fresh_screen_lid_upper_left_top_rim.ply"
    patch_mesh.export(patch_mesh_path)
    source_hashes_after = {name: sha(path) for name, path in fresh_paths.items()}
    if source_hashes_before != source_hashes_after:
        raise FrameIGateCError("fresh_source_mutated")
    terminal = {
        "schema": "tracehoi.FreshFrameITerminal.v1",
        "case_id": config["case_id"],
        "binding_spec": {"path": str(binding_path), "sha256": sha(binding_path)},
        "registration": registration,
        "transform": {"path": str(transform_path), "sha256": sha(transform_path), "matrix": matrix.tolist()},
        "fresh_sources": {name: {"path": str(path), "sha256": source_hashes_after[name]} for name, path in fresh_paths.items()},
        "outputs": {name: {"path": str(path), "sha256": sha(path)} for name, path in output_paths.items()},
        "fresh_patch_face_ids": {"path": str(face_ids_path), "sha256": sha(face_ids_path), "count": int(len(fresh_ids))},
        "fresh_patch_mesh": {"path": str(patch_mesh_path), "sha256": sha(patch_mesh_path)},
        "patch_metrics": patch_metrics,
        "historical_face_ids_reused": False,
        "optimization_updates": 0,
        "eligible_for_gate_c": True,
        "decision": "alapuse02v3n60_fresh_frame_I_closed",
    }
    terminal_path = root / "frame_i_terminal.json"
    atomic_json(terminal_path, terminal)
    return terminal


def run_gate_c(config_path: str | Path, frame_i_terminal_path: str | Path, output_root: str | Path) -> dict[str, Any]:
    config = load_json(config_path, "tracehoi.FreshFrameIGateCConfig.v1")
    frame_path = Path(frame_i_terminal_path)
    frame = load_json(frame_path, "tracehoi.FreshFrameITerminal.v1")
    if frame.get("decision") != "alapuse02v3n60_fresh_frame_I_closed" or frame.get("eligible_for_gate_c") is not True:
        raise FrameIGateCError("frame_i_not_closed")
    if frame.get("optimization_updates") != 0 or frame.get("historical_face_ids_reused") is not False:
        raise FrameIGateCError("frame_i_boundary")
    binding_path = checked_record(frame["binding_spec"], "binding_spec")
    binding = load_json(binding_path, "tracehoi.FreshGateAToFrameIGateCBindingSpec.v1")
    hand_path = checked_record(binding["historical_reference_owners"]["hand_in_I"], "hand_in_I")
    object_path = checked_record(frame["outputs"]["whole_object"], "whole_object_in_I")
    screen_path = checked_record(frame["outputs"]["screen_lid"], "screen_lid_in_I")
    keyboard_path = checked_record(frame["outputs"]["keyboard_base"], "keyboard_base_in_I")
    patch_ids_path = checked_record(frame["fresh_patch_face_ids"], "fresh_patch_face_ids")
    hand = load_mesh(hand_path)
    object_mesh = load_mesh(object_path)
    screen = load_mesh(screen_path)
    keyboard = load_mesh(keyboard_path)
    patch_ids = np.asarray(np.load(patch_ids_path), dtype=np.int64)
    if len(patch_ids) == 0 or int(patch_ids.max()) >= len(screen.faces):
        raise FrameIGateCError("fresh_patch_range")
    semantic = config["semantic_contract"]
    if list(semantic["active_fingers"]) != ["index", "middle"]:
        raise FrameIGateCError("active_finger_contract")
    if binding.get("active_object_part") != "screen_lid":
        raise FrameIGateCError("active_part_contract")
    tip_ids = [int(config["finger_tip_vertex_ids"][finger]) for finger in semantic["active_fingers"]]
    if min(tip_ids) < 0 or max(tip_ids) >= len(hand.vertices):
        raise FrameIGateCError("tip_vertex_range")
    tips = np.asarray(hand.vertices, dtype=np.float64)[tip_ids]
    patch_centers = np.asarray(screen.triangles_center, dtype=np.float64)[patch_ids]
    keyboard_centers = np.asarray(keyboard.triangles_center, dtype=np.float64)
    target_distances = cKDTree(patch_centers).query(tips, k=1)[0]
    forbidden_distances = cKDTree(keyboard_centers).query(tips, k=1)[0]
    object_diagonal = float(np.linalg.norm(object_mesh.extents))
    hand_diagonal = float(np.linalg.norm(hand.extents))
    if object_diagonal <= 1e-12 or hand_diagonal <= 1e-12:
        raise FrameIGateCError("gate_c_extent")
    metrics = {
        "object_diagonal": object_diagonal,
        "hand_to_object_diagonal_ratio": hand_diagonal / object_diagonal,
        "active_tip_target_distances": target_distances.tolist(),
        "active_tip_forbidden_distances": forbidden_distances.tolist(),
        "active_tip_target_normalized_max": float(target_distances.max() / object_diagonal),
        "active_tip_target_normalized_mean": float(target_distances.mean() / object_diagonal),
        "active_tip_forbidden_normalized_mean": float(forbidden_distances.mean() / object_diagonal),
    }
    policy = config["gate_c_policy"]
    errors = []
    if not np.isfinite(hand.vertices).all() or not np.isfinite(object_mesh.vertices).all():
        errors.append("nonfinite_geometry")
    if not float(policy["hand_object_diagonal_ratio_min"]) <= metrics["hand_to_object_diagonal_ratio"] <= float(policy["hand_object_diagonal_ratio_max"]):
        errors.append("hand_object_scale")
    if metrics["active_tip_target_normalized_max"] > float(policy["active_tip_target_normalized_max"]):
        errors.append("active_tip_not_correctable")
    if metrics["active_tip_target_normalized_mean"] > metrics["active_tip_forbidden_normalized_mean"] + float(policy["target_preference_margin"]):
        errors.append("forbidden_part_preferred")
    if errors:
        raise FrameIGateCError("gate_c_hold:" + ",".join(errors) + ":" + json.dumps(metrics, sort_keys=True))
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    terminal = {
        "schema": "tracehoi.FreshGateCTerminal.v1",
        "case_id": config["case_id"],
        "frame_i_terminal": {"path": str(frame_path), "sha256": sha(frame_path)},
        "hand_in_I": {"path": str(hand_path), "sha256": sha(hand_path)},
        "selected_hand_identity": semantic["selected_hand_identity"],
        "active_fingers": list(semantic["active_fingers"]),
        "active_object_part": semantic["object_part"],
        "active_object_region": semantic["object_region_key"],
        "metrics": metrics,
        "optimization_updates": 0,
        "eligible_for_d0": True,
        "decision": "alapuse02v3n60_fresh_gate_C_zero_update_closed",
    }
    terminal_path = root / "gate_c_terminal.json"
    atomic_json(terminal_path, terminal)
    return terminal

_ACCEPTED_LID_ROUTE_V1 = True
_LEGACY_RUN_FRAME_I = run_frame_i
_LEGACY_RUN_GATE_C = run_gate_c


def _accepted_record(path: Path) -> dict[str, Any]:
    return {"path": str(path), "sha256": sha(path)}


def _accepted_full_part_metrics(
    hand: trimesh.Trimesh,
    whole: trimesh.Trimesh,
    screen: trimesh.Trimesh,
    keyboard: trimesh.Trimesh,
    tip_ids: list[int],
) -> dict[str, Any]:
    if min(tip_ids) < 0 or max(tip_ids) >= len(hand.vertices):
        raise FrameIGateCError("tip_vertex_range")
    tips = np.asarray(hand.vertices, dtype=np.float64)[tip_ids]
    target = cKDTree(np.asarray(screen.vertices, dtype=np.float64)).query(tips, k=1)[0]
    forbidden = cKDTree(np.asarray(keyboard.vertices, dtype=np.float64)).query(tips, k=1)[0]
    object_diagonal = float(np.linalg.norm(whole.extents))
    hand_diagonal = float(np.linalg.norm(hand.extents))
    if object_diagonal <= 1e-12 or hand_diagonal <= 1e-12:
        raise FrameIGateCError("accepted_extent")
    return {
        "object_diagonal": object_diagonal,
        "hand_to_object_diagonal_ratio": hand_diagonal / object_diagonal,
        "active_tip_target_distances": target.tolist(),
        "active_tip_forbidden_distances": forbidden.tolist(),
        "active_tip_target_normalized_max": float(target.max() / object_diagonal),
        "active_tip_target_normalized_mean": float(target.mean() / object_diagonal),
        "active_tip_forbidden_normalized_mean": float(forbidden.mean() / object_diagonal),
        "each_active_tip_prefers_screen_lid": bool(np.all(target < forbidden)),
        "target_geometry": "full_screen_lid_vertices",
        "forbidden_geometry": "full_keyboard_base_vertices",
    }


def _accepted_metrics_hold(metrics: Mapping[str, Any], policy: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    ratio = float(metrics["hand_to_object_diagonal_ratio"])
    if not float(policy["hand_object_diagonal_ratio_min"]) <= ratio <= float(policy["hand_object_diagonal_ratio_max"]):
        errors.append("hand_object_scale")
    if float(metrics["active_tip_target_normalized_max"]) > float(policy["active_tip_target_normalized_max"]):
        errors.append("active_tip_not_correctable")
    if metrics["each_active_tip_prefers_screen_lid"] is not True:
        errors.append("keyboard_base_preferred")
    return errors


def _accepted_patch_ids(screen: trimesh.Trimesh, tips: np.ndarray) -> np.ndarray:
    centers = np.asarray(screen.triangles_center, dtype=np.float64)
    count = min(32, len(centers))
    if count < 1:
        raise FrameIGateCError("accepted_screen_faces")
    distances = np.linalg.norm(centers - np.asarray(tips, dtype=np.float64).mean(axis=0), axis=1)
    return np.sort(np.argsort(distances)[:count].astype(np.int64))


def _run_accepted_frame_i(
    config: Mapping[str, Any],
    config_path: str | Path,
    output_root: str | Path,
) -> dict[str, Any]:
    root = Path(output_root)
    terminal_path = root / "frame_i_terminal.json"
    accepted_root = root / "accepted_cpu_lid_proximity_v1"
    if terminal_path.exists() or accepted_root.exists():
        raise FrameIGateCError("accepted_route_not_fresh")

    spec_path = checked_record(config["owners"]["accepted_lid_publication_spec"], "accepted_lid_publication_spec")
    spec = load_json(spec_path, "tracehoi.HandSpecificFrameIAcceptedLidPublicationReentrySpec.v1")
    if spec.get("decision") != "hand_specific_frame_I_accepted_lid_publication_and_reentry_spec_closed" or spec.get("errors") != []:
        raise FrameIGateCError("accepted_publication_spec_not_closed")
    review_path = checked_record(spec["accepted_review"], "accepted_review")
    evidence_path = checked_record(spec["accepted_machine_evidence"], "accepted_machine_evidence")
    candidate_path = checked_record(spec["accepted_hand_candidate"], "accepted_hand_candidate")
    topology_path = checked_record(spec["MANO_topology_owner"], "MANO_topology_owner")
    h2m_path = checked_record(spec["object_route"]["H2M"], "H2M")
    binding_path = checked_record(config["owners"]["binding_spec"], "binding_spec")
    if _accepted_record(binding_path) != spec["superseded_live_owners"]["binding_spec"]:
        raise FrameIGateCError("accepted_binding_owner")

    review = load_json(review_path)
    evidence = load_json(evidence_path)
    if review.get("decision") != "hand_specific_frame_I_cpu_adequate_lid_proximity_review_accepted":
        raise FrameIGateCError("accepted_review_decision")
    if review.get("review", {}).get("label") != "accepted_near_screen_lid":
        raise FrameIGateCError("accepted_review_label")
    if evidence.get("decision") != "hand_specific_frame_I_cpu_adequate_lid_proximity_evidence_closed":
        raise FrameIGateCError("accepted_evidence_decision")
    if evidence.get("part_preference", {}).get("screen_lid_preference_passed") is not True:
        raise FrameIGateCError("accepted_evidence_part_preference")

    binding = load_json(binding_path, "tracehoi.FreshGateAToFrameIGateCBindingSpec.v1")
    if binding.get("decision") != "fresh_gate_A_frame_I_gate_C_binding_spec_closed":
        raise FrameIGateCError("binding_not_closed")
    fresh_records = {
        "whole_object": binding["fresh_whole_object"],
        "screen_lid": binding["fresh_part_owners"]["screen_lid"],
        "keyboard_base": binding["fresh_part_owners"]["keyboard_base"],
    }
    fresh_paths = {name: checked_record(value, f"fresh_{name}") for name, value in fresh_records.items()}
    canonical_fresh_records = {name: _accepted_record(path) for name, path in fresh_paths.items()}
    if canonical_fresh_records != spec["object_route"]["fresh_sources"]:
        raise FrameIGateCError("accepted_fresh_source_owner")
    source_hashes_before = {name: sha(path) for name, path in fresh_paths.items()}
    fresh_meshes = {name: load_mesh(path) for name, path in fresh_paths.items()}

    h2m = np.asarray(np.load(h2m_path, allow_pickle=False), dtype=np.float64)
    if h2m.shape != (4, 4) or not np.isfinite(h2m).all() or float(np.linalg.det(h2m[:3, :3])) <= 0.0:
        raise FrameIGateCError("accepted_H2M")
    transformed = {name: transform_mesh(mesh, h2m) for name, mesh in fresh_meshes.items()}

    topology = load_mesh(topology_path)
    faces = np.asarray(topology.faces, dtype=np.int64)
    if len(topology.vertices) != 778 or faces.ndim != 2 or faces.shape[1] != 3 or int(faces.min()) < 0 or int(faces.max()) >= 778:
        raise FrameIGateCError("accepted_MANO_topology")
    with np.load(candidate_path, allow_pickle=False) as candidate:
        vertices = np.asarray(candidate["aligned_vertices_moge_Nx3"], dtype=np.float64)
        joints = np.asarray(candidate["aligned_joints_moge_21x3"], dtype=np.float64)
    if vertices.shape != (778, 3) or joints.shape != (21, 3) or not np.isfinite(vertices).all() or not np.isfinite(joints).all():
        raise FrameIGateCError("accepted_candidate_shape")
    hand = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    semantic = config["semantic_contract"]
    if list(semantic["active_fingers"]) != ["index", "middle"] or binding.get("active_object_part") != "screen_lid":
        raise FrameIGateCError("accepted_semantic_contract")
    tip_ids = [int(config["finger_tip_vertex_ids"][name]) for name in semantic["active_fingers"]]
    metrics = _accepted_full_part_metrics(
        hand,
        transformed["whole_object"],
        transformed["screen_lid"],
        transformed["keyboard_base"],
        tip_ids,
    )
    holds = _accepted_metrics_hold(metrics, config["gate_c_policy"])
    if holds:
        raise FrameIGateCError("accepted_prepublication_hold:" + ",".join(holds) + ":" + json.dumps(metrics, sort_keys=True))
    patch_ids = _accepted_patch_ids(transformed["screen_lid"], vertices[tip_ids])

    accepted_root.mkdir(parents=True, exist_ok=False)
    hand_path = accepted_root / "accepted_hand_in_I.ply"
    hand.export(hand_path)
    output_paths: dict[str, Path] = {}
    for name, mesh in transformed.items():
        path = accepted_root / f"fresh_{name}_in_I.ply"
        mesh.export(path)
        output_paths[name] = path
    matrix_path = accepted_root / "accepted_H2M.npy"
    np.save(matrix_path, h2m)
    face_ids_path = accepted_root / "screen_lid_local_D0_seed_face_ids.npy"
    np.save(face_ids_path, patch_ids)
    patch_path = accepted_root / "screen_lid_local_D0_seed.ply"
    transformed["screen_lid"].submesh([patch_ids], append=True, repair=False).export(patch_path)
    if source_hashes_before != {name: sha(path) for name, path in fresh_paths.items()}:
        raise FrameIGateCError("fresh_source_mutated")

    accepted_binding = json.loads(json.dumps(binding))
    accepted_binding["historical_reference_owners"]["hand_in_I"] = _accepted_record(hand_path)
    accepted_binding["accepted_hand_publication"] = {
        "route": "accepted_cpu_lid_proximity_v1",
        "publication_spec": _accepted_record(spec_path),
        "review": _accepted_record(review_path),
        "machine_evidence": _accepted_record(evidence_path),
        "candidate": _accepted_record(candidate_path),
        "topology": _accepted_record(topology_path),
        "published_hand": _accepted_record(hand_path),
        "object_transform": _accepted_record(h2m_path),
        "keypoint_nrmse_diagnostic": 0.29848690841524667,
        "another_cpu_fit_authorized": False,
    }
    accepted_binding["accepted_object_outputs"] = {name: _accepted_record(path) for name, path in output_paths.items()}
    accepted_binding_path = accepted_root / "accepted_frame_i_gate_c_binding.json"
    atomic_json(accepted_binding_path, accepted_binding)
    terminal = {
        "schema": "tracehoi.FreshFrameITerminal.v1",
        "case_id": config["case_id"],
        "binding_spec": _accepted_record(accepted_binding_path),
        "registration": {"method": "accepted_cpu_lid_proximity_v1", "historical_similarity_bypassed": True},
        "transform": {"path": str(matrix_path), "sha256": sha(matrix_path), "matrix": h2m.tolist(), "applies_to": list(fresh_records), "applies_to_hand": False},
        "fresh_sources": {name: _accepted_record(path) for name, path in fresh_paths.items()},
        "outputs": {name: _accepted_record(path) for name, path in output_paths.items()},
        "fresh_patch_face_ids": {**_accepted_record(face_ids_path), "count": int(len(patch_ids)), "usage": "downstream_D0_seed_only"},
        "fresh_patch_mesh": {**_accepted_record(patch_path), "usage": "downstream_D0_seed_only"},
        "patch_metrics": {"acceptance_role": "none", "source": "post_acceptance_local_screen_neighborhood"},
        "accepted_lid_publication": {
            "published_hand": _accepted_record(hand_path),
            "publication_spec": _accepted_record(spec_path),
            "review": _accepted_record(review_path),
            "machine_evidence": _accepted_record(evidence_path),
            "full_part_precheck": metrics,
            "keypoint_nrmse_diagnostic": 0.29848690841524667,
        },
        "historical_face_ids_reused": False,
        "optimization_updates": 0,
        "eligible_for_gate_c": True,
        "decision": "alapuse02v3n60_fresh_frame_I_closed",
    }
    atomic_json(terminal_path, terminal)
    return terminal


def run_frame_i(config_path: str | Path, output_root: str | Path) -> dict[str, Any]:
    config = load_json(config_path, "tracehoi.FreshFrameIGateCConfig.v1")
    if "accepted_lid_publication_spec" in config.get("owners", {}):
        return _run_accepted_frame_i(config, config_path, output_root)
    return _LEGACY_RUN_FRAME_I(config_path, output_root)


def _run_accepted_gate_c(
    config: Mapping[str, Any],
    frame_path: Path,
    frame: Mapping[str, Any],
    output_root: str | Path,
) -> dict[str, Any]:
    if frame.get("decision") != "alapuse02v3n60_fresh_frame_I_closed" or frame.get("eligible_for_gate_c") is not True:
        raise FrameIGateCError("frame_i_not_closed")
    if frame.get("optimization_updates") != 0 or frame.get("historical_face_ids_reused") is not False:
        raise FrameIGateCError("frame_i_boundary")
    binding_path = checked_record(frame["binding_spec"], "accepted_binding")
    binding = load_json(binding_path, "tracehoi.FreshGateAToFrameIGateCBindingSpec.v1")
    publication = binding.get("accepted_hand_publication", {})
    if publication.get("route") != "accepted_cpu_lid_proximity_v1":
        raise FrameIGateCError("accepted_binding_route")
    hand_path = checked_record(binding["historical_reference_owners"]["hand_in_I"], "accepted_hand_in_I")
    if _accepted_record(hand_path) != publication.get("published_hand"):
        raise FrameIGateCError("accepted_hand_rebind")
    object_path = checked_record(frame["outputs"]["whole_object"], "whole_object_in_I")
    screen_path = checked_record(frame["outputs"]["screen_lid"], "screen_lid_in_I")
    keyboard_path = checked_record(frame["outputs"]["keyboard_base"], "keyboard_base_in_I")
    checked_record(frame["fresh_patch_face_ids"], "D0_seed_face_ids")
    semantic = config["semantic_contract"]
    tip_ids = [int(config["finger_tip_vertex_ids"][name]) for name in semantic["active_fingers"]]
    hand = load_mesh(hand_path)
    whole = load_mesh(object_path)
    screen = load_mesh(screen_path)
    keyboard = load_mesh(keyboard_path)
    metrics = _accepted_full_part_metrics(hand, whole, screen, keyboard, tip_ids)
    holds = _accepted_metrics_hold(metrics, config["gate_c_policy"])
    if holds:
        raise FrameIGateCError("gate_c_hold:" + ",".join(holds) + ":" + json.dumps(metrics, sort_keys=True))
    root = Path(output_root)
    terminal_path = root / "gate_c_terminal.json"
    if terminal_path.exists():
        raise FrameIGateCError("gate_c_terminal_not_fresh")
    terminal = {
        "schema": "tracehoi.FreshGateCTerminal.v1",
        "case_id": config["case_id"],
        "frame_i_terminal": _accepted_record(frame_path),
        "hand_in_I": _accepted_record(hand_path),
        "selected_hand_identity": semantic["selected_hand_identity"],
        "active_fingers": list(semantic["active_fingers"]),
        "active_object_part": semantic["object_part"],
        "active_object_region": semantic["object_region_key"],
        "metrics": metrics,
        "accepted_lid_publication": publication,
        "optimization_updates": 0,
        "eligible_for_d0": True,
        "decision": "alapuse02v3n60_fresh_gate_C_zero_update_closed",
    }
    atomic_json(terminal_path, terminal)
    return terminal


def run_gate_c(config_path: str | Path, frame_i_terminal_path: str | Path, output_root: str | Path) -> dict[str, Any]:
    config = load_json(config_path, "tracehoi.FreshFrameIGateCConfig.v1")
    frame_path = Path(frame_i_terminal_path)
    frame = load_json(frame_path, "tracehoi.FreshFrameITerminal.v1")
    if frame.get("accepted_lid_publication", {}).get("published_hand"):
        return _run_accepted_gate_c(config, frame_path, frame, output_root)
    return _LEGACY_RUN_GATE_C(config_path, frame_i_terminal_path, output_root)
