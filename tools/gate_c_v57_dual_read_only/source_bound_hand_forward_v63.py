"""v63 source-bound read-only hand forward — implementation scaffold.

Refactor the exact v56 MANO replay, handedness, shared carrier,
mesh_helper_21j order, camera, and target-raster projection into this file.
This module must remain stateless and must never save a nonzero mesh.
"""
from __future__ import annotations

from typing import Any
import numpy as np

IMPLEMENTATION_COMPLETE = False


def load_context(config: dict) -> Any:
    raise RuntimeError("TODO: bind exact immutable v3/v6 source context")


def project_keypoints(context: Any, deltas: dict[str, float]) -> np.ndarray:
    raise RuntimeError("TODO: implement source-faithful ephemeral projection")


def metadata(context: Any) -> dict:
    return {"implementation_complete": IMPLEMENTATION_COMPLETE}
