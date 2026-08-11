from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


REQUIRED_KEYS = (
    "candidate_uid",
    "source_vertices_moge",
    "target_vertices_moge",
    "global_scale",
    "global_rotation_3x3",
    "global_translation_xyz_moge",
    "source_center_xyz_moge",
    "source_identity_tolerance",
)


def load_external_anchor_packet(path: str | Path) -> dict[str, Any]:
    packet_path = Path(path)
    if not packet_path.is_file():
        raise FileNotFoundError(packet_path)
    with np.load(packet_path, allow_pickle=False) as bundle:
        missing = [key for key in REQUIRED_KEYS if key not in bundle.files]
        if missing:
            raise KeyError(f"external anchor packet missing keys: {missing}")
        packet = {key: np.asarray(bundle[key]) for key in bundle.files}
    candidate_uid = str(np.asarray(packet["candidate_uid"]).reshape(()))
    source = np.asarray(packet["source_vertices_moge"], dtype=np.float64)
    target = np.asarray(packet["target_vertices_moge"], dtype=np.float64)
    if candidate_uid != "s100_up":
        raise ValueError(f"unexpected candidate_uid: {candidate_uid}")
    if source.shape != (778, 3) or target.shape != (778, 3):
        raise ValueError(f"expected two 778x3 arrays, got {source.shape} and {target.shape}")
    if not np.isfinite(source).all() or not np.isfinite(target).all():
        raise ValueError("non-finite external anchor vertices")
    return packet


def apply_global_similarity(
    vertices: np.ndarray,
    scale: float,
    rotation_3x3: np.ndarray,
    translation_xyz: np.ndarray,
) -> np.ndarray:
    points = np.asarray(vertices, dtype=np.float64)
    rotation = np.asarray(rotation_3x3, dtype=np.float64)
    translation = np.asarray(translation_xyz, dtype=np.float64).reshape(3)
    if points.shape != (778, 3):
        raise ValueError(f"expected 778x3 vertices, got {points.shape}")
    if rotation.shape != (3, 3):
        raise ValueError(f"expected 3x3 rotation, got {rotation.shape}")
    return float(scale) * (points @ rotation.T) + translation


def centered_translation_from_global_similarity(
    source_vertices: np.ndarray,
    scale: float,
    rotation_3x3: np.ndarray,
    global_translation_xyz: np.ndarray,
) -> np.ndarray:
    source = np.asarray(source_vertices, dtype=np.float64)
    rotation = np.asarray(rotation_3x3, dtype=np.float64)
    global_translation = np.asarray(global_translation_xyz, dtype=np.float64).reshape(3)
    center = source.mean(axis=0)
    return global_translation - center + float(scale) * (center @ rotation.T)


def verify_778_vertex_roundtrip(packet: dict[str, Any]) -> dict[str, float | bool]:
    source = np.asarray(packet["source_vertices_moge"], dtype=np.float64)
    target = np.asarray(packet["target_vertices_moge"], dtype=np.float64)
    replay = apply_global_similarity(
        source,
        float(np.asarray(packet["global_scale"]).reshape(())),
        np.asarray(packet["global_rotation_3x3"], dtype=np.float64),
        np.asarray(packet["global_translation_xyz_moge"], dtype=np.float64),
    )
    delta = replay - target
    maximum = float(np.max(np.abs(delta)))
    rmse = float(np.sqrt(np.mean(np.sum(delta * delta, axis=1))))
    tolerance = float(np.asarray(packet["source_identity_tolerance"]).reshape(()))
    return {
        "max_abs_vertex_error": maximum,
        "vertex_rmse": rmse,
        "source_identity_tolerance": tolerance,
        "pass": bool(maximum <= tolerance),
    }
