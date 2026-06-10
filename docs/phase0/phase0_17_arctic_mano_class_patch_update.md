# Phase 0.17 — ARCTIC MANO Class Patch Update

## Issue

The first MANO 21-joint test used the wrong keyword:

`is_right`

but ARCTIC's `build_mano_aa` expects `is_rhand` or a positional boolean.

## Real blocker

The installed `smplx/body_models.py` already had `vertex_joint_selector` in other model classes, so the first patch script skipped patching the actual `class MANO`.

Inside `class MANO`, the needed line was still commented:

`# joints = self.vertex_joint_selector(vertices, joints)`

## Fix

Uncomment the selector line inside `class MANO`, then rerun the corrected joint-count test.

The processing run should only be retried after both right and left MANO return 21 joints.
