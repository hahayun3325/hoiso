"""Fail-closed adapter template for the Gate-C articulation adequacy probe.

This file MUST be connected to the exact source-bound MANO forward path that
produced the validated zero-update state. Do not substitute a generic SMPL-X
MANO layer, a mesh-regressed helper, a re-exported mesh, or a guessed joint map.

Required contract:

    load_context(config: dict) -> any
    project_keypoints(context, deltas: dict[str, float]) -> ndarray[N, 2]

`deltas` contains ephemeral scalar perturbations named by the parameter
manifest. The adapter may evaluate +h/-h states in memory, but it must not save
or overwrite a nonzero mesh, state file, checkpoint, or placement result.
"""
from __future__ import annotations

from typing import Any
import numpy as np

ADAPTER_CONTRACT_VERSION = 1


def load_context(config: dict) -> Any:
    raise RuntimeError(
        "Adapter is not configured. Bind this template to the exact local "
        "HaMeR/MANO source forward, handedness operation, frozen C1 transform, "
        "camera projection, and source keypoint order."
    )


def project_keypoints(context: Any, deltas: dict[str, float]) -> np.ndarray:
    """Return exact target-raster keypoints in the immutable source order.

    Recommended implementation pattern:
      1. clone the validated zero MANO parameter tensors in memory;
      2. apply each named scalar delta at its source-proven parameter location;
      3. run the exact source MANO wrapper used for the accepted zero state;
      4. apply the exact handedness convention and frozen C1/shared-frame chain;
      5. run the exact live projection helper into the exact target raster;
      6. return only an Nx2 float array; do not export a nonzero mesh.
    """
    raise RuntimeError("project_keypoints() is not implemented")


def metadata(context: Any) -> dict:
    """Optional provenance included in reports."""
    return {}
