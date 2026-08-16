# Dense Gate-A raster regeneration schedule

Generated: 2026-08-16T03:33:40.390488+00:00

## Why this owner exists

Z-order, visibility, contact, and collision losses must compare the hand with
the same object state that the optimizer currently owns. A stale object depth
map can push the hand away from where the object has moved. Rendering the same
object independently for every loss wastes memory and can produce inconsistent
visibility decisions.

## What generates the raster

This step does not call MoGe. It reruns the deterministic signed-camera
triangle renderer on the current Gate-A mesh. The outputs are dense object
depth, valid-pixel coverage, and face IDs. MoGe remains the observation-space
depth/normal target; the Gate-A raster describes the current optimized object.

## Phase schedule

- H0/H1: object frozen. Rasterize once, detach/cache, and share it across all
  hand losses and updates. Invalidate only if the object or camera owner changes.
- O0/J0: object trainable. At the start of every forward iteration, build one
  differentiable raster from the current object vertices. Reuse it for every
  loss in that iteration. After backward/update, discard it; regenerate from
  the updated vertices during the next forward iteration.

The runner must supply a unique iteration key for a moving object. This makes
stale reuse detectable and keeps one coherent raster owner per forward pass.

## Project locations

- Schedule helper: tools/hoiso_d0_objective_contract/dense_raster_schedule.py
- CPU test: tests/hoiso_d0_objective_contract/test_dense_raster_schedule.py
