import numpy as np
import trimesh


def vertices_of(geom):
    return np.asarray(geom.vertices, dtype=np.float64)


def transform_vertices(vertices, scale, R, t):
    return scale * (np.asarray(vertices, dtype=np.float64) @ R.T) + t


def apply_similarity(geom, scale, R, t):
    vertices = transform_vertices(vertices_of(geom), scale, R, t)

    if isinstance(geom, trimesh.PointCloud):
        return trimesh.PointCloud(vertices)

    out = geom.copy()
    out.vertices = vertices
    return out


def bbox_diag(geom):
    v = vertices_of(geom)
    lo = v.min(axis=0)
    hi = v.max(axis=0)
    return float(np.linalg.norm(hi - lo))
