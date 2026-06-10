# Phase 0.17 — ARCTIC NumPy bool Fix

## Problem

After fixing the ARCTIC body-model symlinks, `process_seqs.py` moved past the MANO/SMPL-X path error but failed at:

`AttributeError: module 'numpy' has no attribute 'bool'`

## Cause

The ARCTIC code uses the deprecated NumPy alias `np.bool`, which is removed in newer NumPy versions.

The failing file is:

`/home/fredcui/Projects/arctic/common/object_tensors.py`

## Fix

Replace:

`dtype=np.bool`

with:

`dtype=bool`

## Status

The body-model path issue is solved. The next blocker is only code compatibility with the current NumPy version.
