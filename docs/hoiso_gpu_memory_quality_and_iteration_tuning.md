# HOISO-Flow GPU Memory, Quality, and Iteration-Tuning Guide

## Purpose

This guide separates settings that reduce peak VRAM from settings that reduce computation or change alignment quality. It records the current RTX 4090 fast-track profile and a reproducible procedure for choosing object and joint iteration budgets.

## Current bounded profile

- GPU: NVIDIA GeForce RTX 4090, 24 GiB.
- Runtime observed: PyTorch 2.5.0 with CUDA 12.4; driver reports CUDA 12.6.
- Shape model: cached Hunyuan3D-2 fast payload in FP16/offline mode.
- CUDA allocator: `backend:cudaMallocAsync`.
- Input/render raster: 512×512 with render scale 1.0.
- Color render faces per pixel: 1; silhouette faces per pixel: 100.
- Final octree setting: 192.
- Bounded object initialization: hand/object/joint updates = `0/5/0`; Gate-D disabled.
- Hand: frozen external `s100_up` anchor.
- Object: accepted Gate-A laptop mesh, fixed topology and shared rigid root.

## What changes peak VRAM

The strongest peak-memory controls are raster resolution, faces per pixel, object vertex/face count, batch size, latent dimensions, simultaneous model residency, octree resolution, precision, and whether renderer/model tensors are offloaded or released between stages.

Iteration count primarily changes runtime. With a correct loop, each iteration has the same tensor shapes and releases its graph. More iterations can still cause OOM when graphs or loss histories retain tensors, caches grow, or allocator fragmentation accumulates. Therefore, iteration safety must be measured rather than assumed.

FP16 and CPU/model offload usually reduce VRAM. FP16 may introduce small numerical changes; offload should preserve the objective but increases transfer time. Lower raster or geometry resolution can weaken silhouette, edge, and fine-contact gradients. Fewer iterations can stop pose optimization before convergence. None of these settings literally makes a rigid pose “blurry”; they affect surface detail, gradient fidelity, or convergence.

## Quality risks of the five-step object stage

Five updates are a diagnostic initialization rather than a convergence claim. The laptop topology and internal part arrangement are protected, but global translation, rotation, and scale may remain suboptimal. Joint flow can refine a reasonable initialization; it should not be expected to recover from an arbitrary object pose. Gate-D addresses contact and penetration only after joint-flow validation.

## Staircase protocol for choosing the sweet spot

1. Freeze the same case, inputs, seed, model hash, source commit, precision, raster, losses, and initialization.
2. Run each budget in a fresh process so CUDA state and fragmentation do not carry across trials.
3. Start with object budgets `5, 10, 20, 40`; add a larger budget only when quality is still improving and memory remains stable.
4. Record peak allocated and reserved CUDA memory, wall time, per-iteration memory, and any memory-growth slope.
5. Preserve at least 10–15% device headroom. Stop escalation when reserved memory grows across equal-shape iterations or the process approaches the operating headroom.
6. Record loss trajectories, full-raster reprojection and silhouette metrics, object transform deltas, hand drift, topology hashes, contact coverage, penetration, and fixed-camera renders.
7. Choose the smallest iteration count within a preregistered tolerance of the best stable result on calibration/control cases.
8. Confirm the selected budget on held-out cases. Do not tune a stopping threshold on the same demonstration used for the headline result.

## Memory instrumentation requirements

At every stage boundary record `torch.cuda.max_memory_allocated()`, `torch.cuda.max_memory_reserved()`, current allocated/reserved memory, model/offload status, raster size, faces-per-pixel, octree setting, precision, and iteration number. Sample `nvidia-smi` as an external cross-check. Reset peak counters only at a recorded boundary.

An increasing iteration budget should be treated as unsafe when memory grows monotonically rather than reaching a steady plateau. Investigate retained tensors, lists of GPU losses, `retain_graph`, renderer caches, and unreleased meshes before reducing quality settings.

## Generalization checklist for ARCTIC

- Use a case manifest for RGB, masks, camera/H2M, runtime MANO source, object mesh, part labels, topology, and hashes.
- Generate or rebind the anchor against the actual runtime hand source.
- Validate left/right hand, vertex order, face topology, units, and coordinate frames.
- Encode category kinematics: laptop and microwave hinges, scissors pivot/blade coupling, and legal articulation limits.
- Define category-appropriate contact regions and collision exclusions.
- Calibrate gates and early stopping on training/control cases; evaluate untouched objects and viewpoints.
- Preserve before-object, before-joint, after-joint, and after-Gate-D checkpoints with identical render conventions.
- Report aggregate success, failure reasons, VRAM, runtime, and quality—not only selected visual examples.

## Experiment record template

For each run record: case UID, object category, commit, command hash, input hashes, seed, model/cache hash, precision, raster, render settings, octree setting, hand/object/joint budgets, loss weights, peak allocated/reserved VRAM, runtime, final losses and metrics, topology/hand-drift checks, checkpoint hashes, render paths, and decision.

## Interpretation rule

Memory-only measures such as safe offload or tensor release may preserve quality. Reduced iterations, precision, raster resolution, omitted losses, or changed stage coupling may change quality and require an ablation. A fast-track and full run are comparable only when their relevant settings and independently measured outputs agree within frozen tolerances.
