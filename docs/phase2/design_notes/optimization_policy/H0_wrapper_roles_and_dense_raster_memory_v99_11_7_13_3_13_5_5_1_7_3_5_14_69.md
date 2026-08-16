# H0 wrapper roles and dense-raster memory policy

Generated: 2026-08-16T03:57:00.596832+00:00

## Runner roles

The general hand-optimization pipeline remains the numerical engine. The
versioned `run_d0_h0_global_rt` file is a control wrapper: it loads the H0
contract, resolves the permitted global rotation/translation parameters,
binds the compiled D0 losses and frozen object raster, and owns checkpoints
and rollback. Debug pipelines and the semantic compiler are dependencies, not
alternative production runners.

Do not create a second optimization engine. Reuse the existing wrapper when
all seams are present; otherwise patch only the missing seams in a reviewed
versioned successor.

## Raster memory

At 512x512, float32 depth is approximately 1 MiB, int64 face ID 2 MiB, and a
boolean valid mask 0.25 MiB. H0/H1 cache one detached fixed-object raster, so
their persistent increase is about 3.25 MiB plus container overhead.

O0/J0 keep one differentiable raster per forward iteration. With
`faces_per_pixel=1`, raw z/face/distance/barycentric buffers are roughly 7 MiB;
renderer and autograd intermediates can raise the true peak into the tens of
MiB. Share this raster across all loss terms, clear it after backward, never
retain its graph across updates, and measure peak CUDA allocation in the first
bounded O0/J0 probe.
