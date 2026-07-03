# alapuse01 — relabel v1 projection failure note

## Current result

Manual lid/base masks are usable.
Camera intrinsics and depth are available.
Relabel-only audit passes.

However, gate_d0_fit_v1_relabel_parts.py failed during component relabeling.

## Likely cause

The 3D active part meshes are not projecting into the 2D crop/mask frame as expected.

This can happen if:

- the mesh is not in the MoGe camera frame,
- the camera uses a different axis convention,
- the forward axis should be -Z instead of +Z,
- y-axis needs flipping,
- or the mesh needs the h2m / m2h transform before projection.

## Decision

Do not run articulated fitting yet.

First run a projection-frame probe and then rerun relabel with the best transform candidate.

## Next step

Run:

- gate_d0_fit_v1_projection_frame_probe.py
- gate_d0_fit_v1_relabel_parts_safe.py

If projection-based relabel still fails, use manual component relabel v1b as a fallback.
