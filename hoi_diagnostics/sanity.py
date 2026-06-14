import numpy as np

from .alignment import bbox_diag, vertices_of


def assert_geometry_basic(geom, name):
    warnings = []

    v = vertices_of(geom)
    if len(v) == 0:
        raise ValueError(f"{name}: empty vertices")

    if not np.isfinite(v).all():
        raise ValueError(f"{name}: non-finite vertices")

    if hasattr(geom, "faces"):
        if len(geom.faces) == 0:
            warnings.append(f"{name}: no faces / point cloud")
        elif not getattr(geom, "is_watertight", False):
            warnings.append(f"{name}: non-watertight")

    return warnings


def assert_hand_bbox_m(hand_geom, sample_id, min_diag_m, max_diag_m):
    diag = bbox_diag(hand_geom)

    if not (min_diag_m <= diag <= max_diag_m):
        raise ValueError(
            f"{sample_id}: aligned hand bbox diagonal {diag:.4f} m "
            f"outside [{min_diag_m}, {max_diag_m}] m. "
            "Check unit or cached transform."
        )

    return diag
