from __future__ import annotations

from pathlib import Path
from typing import Any

import hashlib
import importlib.util
import json
import os

import numpy as np


def _sha256_array(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def _load_adapter(path: str | Path):
    adapter_path = Path(path)
    spec = importlib.util.spec_from_file_location("foho_external_anchor_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load external anchor adapter: {adapter_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rotation_matrix_to_quaternion_wxyz(matrix: np.ndarray) -> np.ndarray:
    value = np.asarray(matrix, dtype=np.float64)
    if value.shape != (3, 3):
        raise ValueError(f"rotation must be 3x3, got {value.shape}")
    quaternion = np.empty(4, dtype=np.float64)
    trace = float(np.trace(value))
    if trace > 0.0:
        scale = (trace + 1.0) ** 0.5 * 2.0
        quaternion[:] = [
            scale / 4.0,
            (value[2, 1] - value[1, 2]) / scale,
            (value[0, 2] - value[2, 0]) / scale,
            (value[1, 0] - value[0, 1]) / scale,
        ]
    else:
        index = int(np.argmax(np.diag(value)))
        second, third = (index + 1) % 3, (index + 2) % 3
        scale = (1.0 + value[index, index] - value[second, second] - value[third, third]) ** 0.5 * 2.0
        quaternion[0] = (value[third, second] - value[second, third]) / scale
        quaternion[index + 1] = scale / 4.0
        quaternion[second + 1] = (value[second, index] + value[index, second]) / scale
        quaternion[third + 1] = (value[third, index] + value[index, third]) / scale
    quaternion /= np.linalg.norm(quaternion)
    return quaternion


def _fresh_path(name: str) -> Path:
    path = Path(os.environ[name])
    if path.exists():
        raise RuntimeError(f"fresh output collision for {name}: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _make_transformed_hand(
    torch_module: Any,
    device: Any,
    mano_mesh_moge: Any,
    scale_hand: Any,
    trans_hand: Any,
    rotation_hand: Any,
    quaternion_to_matrix: Any,
    transform_mesh_around_center_w_scale: Any,
):
    transform = torch_module.eye(4, device=device)
    rotation = quaternion_to_matrix(rotation_hand).float()
    while rotation.ndim > 2 and rotation.shape[0] == 1:
        rotation = rotation[0]
    transform[:3, :3] = rotation.reshape(3, 3)
    transform[:3, 3] = trans_hand.reshape(-1)[:3]
    mesh = transform_mesh_around_center_w_scale(mano_mesh_moge, transform, scale_hand)
    return mesh, transform


def activate_external_anchor(
    *,
    torch_module: Any,
    device: Any,
    mano_mesh_moge: Any,
    scale_hand: Any,
    trans_hand: Any,
    rotation_hand: Any,
    quaternion_to_matrix: Any,
    transform_mesh_around_center_w_scale: Any,
) -> tuple[Any, dict[str, Any]]:
    adapter = _load_adapter(os.environ["FOHO_EXTERNAL_HAND_ANCHOR_ADAPTER"])
    packet = adapter.load_external_anchor_packet(os.environ["FOHO_EXTERNAL_HAND_ANCHOR_NPZ"])
    roundtrip = adapter.verify_778_vertex_roundtrip(packet)
    if roundtrip.get("pass") is not True:
        raise RuntimeError(f"frozen packet roundtrip failed: {roundtrip}")

    source = np.asarray(packet["source_vertices_moge"], dtype=np.float64)
    target = np.asarray(packet["target_vertices_moge"], dtype=np.float64)
    tolerance = float(np.asarray(packet["source_identity_tolerance"]).reshape(()))
    runtime_source = mano_mesh_moge.verts_packed().detach().cpu().numpy().astype(np.float64)
    source_error = float(np.max(np.abs(runtime_source - source)))
    if runtime_source.shape != (778, 3) or source_error > tolerance:
        raise RuntimeError(f"live source identity failed: shape={runtime_source.shape} error={source_error}")

    scale_value = float(np.asarray(packet["global_scale"]).reshape(()))
    rotation_value = np.asarray(packet["global_rotation_3x3"], dtype=np.float64)
    centered_translation = adapter.centered_translation_from_global_similarity(
        source,
        scale_value,
        rotation_value,
        np.asarray(packet["global_translation_xyz_moge"], dtype=np.float64),
    )
    quaternion = _rotation_matrix_to_quaternion_wxyz(rotation_value)
    with torch_module.no_grad():
        scale_hand.copy_(torch_module.as_tensor(scale_value, dtype=scale_hand.dtype, device=scale_hand.device).reshape_as(scale_hand))
        trans_hand.copy_(torch_module.as_tensor(centered_translation, dtype=trans_hand.dtype, device=trans_hand.device).reshape_as(trans_hand))
        rotation_hand.copy_(torch_module.as_tensor(quaternion, dtype=rotation_hand.dtype, device=rotation_hand.device).reshape_as(rotation_hand))

    transformed, transform = _make_transformed_hand(
        torch_module,
        device,
        mano_mesh_moge,
        scale_hand,
        trans_hand,
        rotation_hand,
        quaternion_to_matrix,
        transform_mesh_around_center_w_scale,
    )
    runtime_target = transformed.verts_packed().detach().cpu().numpy().astype(np.float64)
    target_error = float(np.max(np.abs(runtime_target - target)))
    faces_before = mano_mesh_moge.faces_packed().detach().cpu().numpy().astype(np.int64)
    faces_after = transformed.faces_packed().detach().cpu().numpy().astype(np.int64)
    faces_equal = bool(np.array_equal(faces_before, faces_after))
    if runtime_target.shape != (778, 3) or target_error > tolerance or not faces_equal:
        raise RuntimeError(f"live external anchor replay failed: target_error={target_error} faces_equal={faces_equal}")

    preflight_path = _fresh_path("FOHO_EXTERNAL_HAND_ANCHOR_PREFLIGHT_JSON")
    zero_step_path = _fresh_path("FOHO_EXTERNAL_HAND_ANCHOR_ZERO_STEP_VERTICES_NPY")
    np.save(zero_step_path, runtime_target)
    preflight = {
        "schema": "s100_up_external_anchor_live_preflight_v99_11_7_13_3_13_4_1",
        "decision": "pass_v99_11_7_13_3_13_4_1_live_778_vertices_and_face_hash",
        "candidate_uid": "s100_up",
        "source_vertex_count": int(runtime_source.shape[0]),
        "target_vertex_count": int(runtime_target.shape[0]),
        "source_max_abs_error": source_error,
        "target_max_abs_error": target_error,
        "tolerance": tolerance,
        "face_count": int(faces_before.shape[0]),
        "face_hash_before": _sha256_array(faces_before),
        "face_hash_after": _sha256_array(faces_after),
        "faces_equal": faces_equal,
        "hand_optimization_steps_executed": 0,
        "joint_flow_steps_authorized": 0,
    }
    preflight_path.write_text(json.dumps(preflight, indent=2) + chr(10))
    state = {
        "anchor_scale": scale_hand.detach().clone(),
        "anchor_translation": trans_hand.detach().clone(),
        "anchor_rotation": rotation_hand.detach().clone(),
        "target_vertices": target,
        "tolerance": tolerance,
        "preflight": preflight,
        "transform": transform.detach().clone(),
    }
    return transformed, state


def restore_external_anchor(
    state: dict[str, Any],
    *,
    torch_module: Any,
    device: Any,
    mano_mesh_moge: Any,
    scale_hand: Any,
    trans_hand: Any,
    rotation_hand: Any,
    quaternion_to_matrix: Any,
    transform_mesh_around_center_w_scale: Any,
):
    with torch_module.no_grad():
        scale_hand.copy_(state["anchor_scale"])
        trans_hand.copy_(state["anchor_translation"])
        rotation_hand.copy_(state["anchor_rotation"])
    transformed, _ = _make_transformed_hand(
        torch_module,
        device,
        mano_mesh_moge,
        scale_hand,
        trans_hand,
        rotation_hand,
        quaternion_to_matrix,
        transform_mesh_around_center_w_scale,
    )
    return transformed


def assert_object_guidance_excludes_frozen_hand(
    value: Any,
    scale_hand: Any,
    trans_hand: Any,
    rotation_hand: Any,
) -> None:
    def contains(item: Any) -> bool:
        if item is scale_hand or item is trans_hand or item is rotation_hand:
            return True
        if isinstance(item, dict):
            return any(contains(child) for child in item.values())
        if isinstance(item, (list, tuple)):
            return any(contains(child) for child in item)
        return False
    if contains(value):
        raise RuntimeError("Phase 1.5 object guidance unexpectedly contains a frozen hand parameter")


def _cpu_clone(torch_module: Any, value: Any) -> Any:
    if torch_module.is_tensor(value):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {key: _cpu_clone(torch_module, child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_cpu_clone(torch_module, child) for child in value)
    return value


def write_post_object_checkpoint(
    state: dict[str, Any],
    *,
    torch_module: Any,
    transformed_hand_mesh: Any,
    transformed_object_mesh: Any,
    scale_hand: Any,
    trans_hand: Any,
    rotation_hand: Any,
    object_RT: Any,
    object_scale: Any,
    runtime_locals: dict[str, Any],
) -> dict[str, Any]:
    checkpoint_path = _fresh_path("FOHO_POST_OBJECT_CHECKPOINT_PT")
    geometry_path = _fresh_path("FOHO_POST_OBJECT_GEOMETRY_NPZ")
    receipt_path = _fresh_path("FOHO_POST_OBJECT_RECEIPT_JSON")
    hand_vertices = transformed_hand_mesh.verts_packed().detach().cpu().numpy().astype(np.float64)
    hand_faces = transformed_hand_mesh.faces_packed().detach().cpu().numpy().astype(np.int64)
    object_vertices = transformed_object_mesh.verts_packed().detach().cpu().numpy().astype(np.float64)
    object_faces = transformed_object_mesh.faces_packed().detach().cpu().numpy().astype(np.int64)
    hand_drift = float(np.max(np.abs(hand_vertices - state["target_vertices"])))
    if hand_vertices.shape != (778, 3) or hand_drift > float(state["tolerance"]):
        raise RuntimeError(f"frozen hand drifted during object stage: {hand_drift}")
    np.savez_compressed(
        geometry_path,
        hand_vertices_moge=hand_vertices,
        hand_faces=hand_faces,
        object_vertices_moge=object_vertices,
        object_faces=object_faces,
    )
    torch_module.save({
        "schema": "post_object_before_joint_flow_checkpoint_v99_11_7_13_3_13_4_1",
        "candidate_uid": "s100_up",
        "scale_hand": _cpu_clone(torch_module, scale_hand),
        "trans_hand": _cpu_clone(torch_module, trans_hand),
        "rotation_hand_wxyz": _cpu_clone(torch_module, rotation_hand),
        "object_RT": _cpu_clone(torch_module, object_RT),
        "object_scale": _cpu_clone(torch_module, object_scale),
        "latents": _cpu_clone(torch_module, runtime_locals.get("latents")),
        "noise_pred": _cpu_clone(torch_module, runtime_locals.get("noise_pred")),
        "noise_pred_obj": _cpu_clone(torch_module, runtime_locals.get("noise_pred_obj")),
        "optimization_steps_hand": 0,
        "optimization_steps_joint": 0,
    }, checkpoint_path)
    receipt = {
        "schema": "post_object_before_joint_flow_receipt_v99_11_7_13_3_13_4_1",
        "decision": "pass_v99_11_7_13_3_13_4_1_complete_preflow_hand_object_checkpoint_written",
        "candidate_uid": "s100_up",
        "hand_vertex_count": int(hand_vertices.shape[0]),
        "hand_face_count": int(hand_faces.shape[0]),
        "hand_max_abs_drift": hand_drift,
        "object_vertex_count": int(object_vertices.shape[0]),
        "object_face_count": int(object_faces.shape[0]),
        "input_image": os.environ.get("FOHO_INPUT_IMAGE_PATH"),
        "camera_artifact": os.environ.get("FOHO_CAMERA_ARTIFACT_PATH"),
        "mask_manifest": os.environ.get("FOHO_MASK_MANIFEST_PATH"),
        "joint_flow_executed": False,
        "gate_d_executed": False,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + chr(10))
    return receipt
