from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any, List
import numpy as np
import trimesh


@dataclass
class ObjectCandidate:
    name: str
    mesh_path: Path
    pose_path: Optional[Path] = None
    source_stage: str = ""
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ObjectSelectionResult:
    selected_name: str
    selected_mesh_path: Path
    scores: Dict[str, Dict[str, Any]]


def load_mesh(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load(path, process=False)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh


def mesh_completeness_score(path: Path) -> Dict[str, Any]:
    mesh = load_mesh(path)
    comps = mesh.split(only_watertight=False)
    faces = np.array([len(c.faces) for c in comps], dtype=float)
    largest_ratio = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0.0
    fragmentation_score = (len(comps) - 1) + (1.0 - largest_ratio)

    return {
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "components": int(len(comps)),
        "largest_face_ratio": float(largest_ratio),
        "fragmentation_score": float(fragmentation_score),
        "watertight": bool(mesh.is_watertight),
    }


def scalar_object_score(metrics: Dict[str, Any]) -> float:
    """Lower is better."""
    return float(metrics["fragmentation_score"]) - float(metrics["largest_face_ratio"])


def select_object_candidate(candidates: List[ObjectCandidate]) -> ObjectSelectionResult:
    """Select the best object-only candidate.

    Important:
    - Candidates should be object-only meshes.
    - This selector should be inserted before final alignment.
    - It should not be used as blind post-hoc scene replacement.
    """
    if not candidates:
        raise ValueError("No object candidates were provided.")

    scores: Dict[str, Dict[str, Any]] = {}
    best = None
    best_scalar = None

    for cand in candidates:
        metrics = mesh_completeness_score(cand.mesh_path)
        scores[cand.name] = metrics
        scalar = scalar_object_score(metrics)

        if best is None or scalar < best_scalar:
            best = cand
            best_scalar = scalar

    return ObjectSelectionResult(
        selected_name=best.name,
        selected_mesh_path=best.mesh_path,
        scores=scores,
    )
