# Phase 0.17 — ARCTIC MANO 21-Joint Fix

## Problem

After fixing ARCTIC body-model paths and the NumPy `np.bool` issue, `process_seqs.py` failed at:

`assert mano_l["joints.left"].shape[1] == 21`

## Cause

The installed `smplx` MANO implementation returns 16 MANO joints by default. ARCTIC expects 21 joints.

## Fix

Patch the installed `smplx/body_models.py` MANO forward pass so that after:

`joints = vertices2joints(self.J_regressor, vertices)`

it also runs:

`joints = self.vertex_joint_selector(vertices, joints)`

## Important caution

Only `np.bool` was a real NumPy deprecated-alias blocker. Valid dtypes like `np.float32` and `np.int64` should not be broadly replaced.
