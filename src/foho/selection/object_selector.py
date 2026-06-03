from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any
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
    largest = faces.max() / max(len(mesh.faces), 1) if len(faces) else 0.0
    frag = (len(comps) - 1) + (1.0 - largest)

    return {
        "vertices": len(mesh.vertices),
        "faces": len(mesh.faces),
        "components": len(comps),
        "largest_face_ratio": float(largest),
        "fragmentation_score": float(frag),
        "watertight": bool(mesh.is_watertight),
    }


def select_object_candidate(candidates: list[ObjectCandidate]) -> ObjectSelectionResult:
    """Select the best object candidate by simple completeness score.

    This is a placeholder for the Phase 4.2 -> Phase 4.3 selector.

    Important:
    - candidates should be object-only meshes,
    - this should not be used for blind post-hoc scene replacement.
    """
    if not candidates:
        raise ValueError("No object candidates were provided.")

    scores: Dict[str, Dict[str, Any]] = {}

    best = None
    best_score = None

    for cand in candidates:
        s = mesh_completeness_score(cand.mesh_path)
        scores[cand.name] = s

        # Lower fragmentation is better. Higher largest ratio is better.
        scalar = float(s["fragmentation_score"]) - float(s["largest_face_ratio"])

        if best is None or scalar < best_score:
            best = cand
            best_score = scalar

    return ObjectSelectionResult(
        selected_name=best.name,
        selected_mesh_path=best.mesh_path,
        scores=scores,
    )
