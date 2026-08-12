from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch


def _numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach().cpu()
    return np.asarray(value)


def _clone(value: Any) -> Any:
    if hasattr(value, "detach"):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {key: _clone(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_clone(item) for item in value)
    return value


def _mesh_arrays(mesh: Any) -> tuple[np.ndarray, np.ndarray]:
    if hasattr(mesh, "verts_packed") and hasattr(mesh, "faces_packed"):
        vertices, faces = mesh.verts_packed(), mesh.faces_packed()
    elif hasattr(mesh, "vertices") and hasattr(mesh, "faces"):
        vertices, faces = mesh.vertices, mesh.faces
    elif isinstance(mesh, dict) and "vertices" in mesh and "faces" in mesh:
        vertices, faces = mesh["vertices"], mesh["faces"]
    else:
        raise TypeError(f"unsupported mesh type: {type(mesh).__name__}")
    vertices = _numpy(vertices)
    faces = _numpy(faces)
    if vertices.ndim != 2 or vertices.shape[1] != 3:
        raise ValueError(f"invalid vertex shape: {vertices.shape}")
    if faces.ndim != 2 or faces.shape[1] != 3:
        raise ValueError(f"invalid face shape: {faces.shape}")
    return vertices, faces


def _sha256(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).view(np.uint8)).hexdigest()


def write_zero_step_checkpoint(
    output_root: str | None,
    *,
    transformed_obj_mesh: Any,
    anchor_state: Any,
    scale_obj: Any,
    trans_obj: Any,
    rotation_obj: Any,
    noise_pred_obj: Any,
) -> dict[str, Any] | None:
    if not output_root:
        return None
    root = Path(output_root)
    if root.exists():
        raise FileExistsError(f"zero-step output already exists: {root}")
    root.mkdir(parents=True)

    hand_mesh = anchor_state.get("anchor_target_mesh") if isinstance(anchor_state, dict) else getattr(anchor_state, "anchor_target_mesh", None)
    if hand_mesh is None:
        raise KeyError("anchor_target_mesh is unavailable")

    object_vertices, object_faces = _mesh_arrays(transformed_obj_mesh)
    hand_vertices, hand_faces = _mesh_arrays(hand_mesh)
    geometry = root / "hand_object_geometry_step_zero.npz"
    state = root / "state_step_zero.pt"
    receipt = root / "receipt_step_zero.json"

    np.savez_compressed(
        geometry,
        object_vertices_moge=object_vertices,
        object_faces=object_faces,
        hand_vertices_moge=hand_vertices,
        hand_faces=hand_faces,
    )
    torch.save(
        {
            "schema": "alapuse02v3n60_object_preupdate_step_zero_v1",
            "scale_obj": _clone(scale_obj),
            "trans_obj": _clone(trans_obj),
            "rotation_obj": _clone(rotation_obj),
            "noise_pred_obj": _clone(noise_pred_obj),
        },
        state,
    )
    payload = {
        "schema": "alapuse02v3n60_object_preupdate_step_zero_v1",
        "semantics": "first_forward_geometry_before_backward_and_optimizer_step",
        "object_vertex_count": int(object_vertices.shape[0]),
        "object_face_count": int(object_faces.shape[0]),
        "hand_vertex_count": int(hand_vertices.shape[0]),
        "hand_face_count": int(hand_faces.shape[0]),
        "object_vertices_sha256": _sha256(object_vertices),
        "object_faces_sha256": _sha256(object_faces),
        "hand_vertices_sha256": _sha256(hand_vertices),
        "hand_faces_sha256": _sha256(hand_faces),
        "optimizer_updates_executed": 0,
        "geometry": str(geometry),
        "state": str(state),
    }
    receipt.write_text(json.dumps(payload, indent=2) + chr(10))
    return payload
