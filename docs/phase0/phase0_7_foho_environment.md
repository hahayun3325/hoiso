# Phase 0.7 — Create and Repair the `foho` Environment

## Goal

Create the official FollowMyHold conda environment before fetching weights and running the pipeline.

## Initial issue

The official setup script created the `foho` environment and installed PyTorch, but stopped early because plain `pip install detectron2` could not find a compatible wheel.

## Repair actions

The environment was repaired manually:

- Installed common FollowMyHold dependencies.
- Installed Kaolin 0.17.0.
- Installed Detectron2 from source.
- Built the hand-object detector CUDA extension.
- Built PyTorch3D from source.
- Installed remaining Python dependencies.
- Repaired `mmcv==1.3.9` using `--no-build-isolation`.
- Installed MMPose / MMEngine.
- Re-pinned NumPy, diffusers, transformers, and Hugging Face Hub.
- Fixed the missing Google API dependency for `google.generativeai`.

## Verified core stack

- Python: 3.10.20
- PyTorch: 2.5.0+cu124
- Torch CUDA: 12.4
- CUDA available: True
- GPU: NVIDIA GeForce RTX 4090
- CUDA matmul test: passed

## Final verification

The final dependency import check passed:

ALL_IMPORTS_OK

The FollowMyHold source import check passed:

FOHO_IMPORTS_OK

## Decision

Phase 0.7 passed.

The machine is ready for Phase 0.8:

- fetch bundled weights/data
- verify HaMeR / WiLoR assets
- prepare manual detector and MANO assets  
