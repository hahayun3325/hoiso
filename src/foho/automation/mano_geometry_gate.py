from __future__ import annotations
from collections.abc import Sequence
from pathlib import Path
import math
import numpy as np

class ManoGeometryError(RuntimeError):
    pass

def audit_vertices(vertices, faces=None, *, expected_vertices=None,
                   maximum_axis_ratio=25.0, minimum_extent=1e-8):
    points = np.asarray(vertices, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3 or points.shape[0] < 100:
        raise ManoGeometryError("MANO vertices must be finite Nx3 with N >= 100")
    if not np.isfinite(points).all():
        raise ManoGeometryError("MANO vertices contain nonfinite values")
    if expected_vertices is not None and points.shape[0] != int(expected_vertices):
        raise ManoGeometryError("MANO topology vertex count changed")
    extent = np.ptp(points, axis=0)
    if not np.isfinite(extent).all() or np.any(extent <= float(minimum_extent)):
        raise ManoGeometryError("MANO has a collapsed axis")
    ratio = float(np.max(extent) / np.min(extent))
    if not math.isfinite(ratio) or ratio > float(maximum_axis_ratio):
        raise ManoGeometryError("MANO has an implausible axis ratio")
    face_count = None
    if faces is not None:
        triangles = np.asarray(faces)
        if triangles.ndim != 2 or triangles.shape[1] != 3 or triangles.shape[0] < 100:
            raise ManoGeometryError("MANO faces must be Mx3 with M >= 100")
        if not np.issubdtype(triangles.dtype, np.integer):
            raise ManoGeometryError("MANO face indices must be integers")
        if triangles.min() < 0 or triangles.max() >= points.shape[0]:
            raise ManoGeometryError("MANO face index is out of range")
        face_count = int(triangles.shape[0])
    return {"vertices": int(points.shape[0]), "faces": face_count,
            "extent_xyz": extent.tolist(), "axis_ratio": ratio,
            "finite": True, "decision": "mano_geometry_gate_closed"}

def audit_mesh(path: str | Path, *, expected_vertices=None,
               maximum_axis_ratio=25.0, minimum_extent=1e-8):
    import trimesh
    owner = Path(path)
    if not owner.is_file():
        raise FileNotFoundError(str(owner))
    mesh = trimesh.load(owner, process=False, force="mesh")
    return audit_vertices(mesh.vertices, mesh.faces,
                          expected_vertices=expected_vertices,
                          maximum_axis_ratio=maximum_axis_ratio,
                          minimum_extent=minimum_extent)
