# Phase 0.7 — Create and Repair the `foho` Environment

## Goal

Create the official FollowMyHold conda environment before fetching weights and running the pipeline.

## Initial result

The official environment script started successfully and created the `foho` conda environment, but stopped during dependency installation because plain `pip install detectron2` could not find a compatible package.

## Verified working core

Python: 3.10.20
PyTorch: 2.5.0+cu124
Torch CUDA: 12.4
CUDA available: True
GPU: NVIDIA GeForce RTX 4090

A CUDA tensor matrix multiplication test succeeded.

## Repair plan

The missing dependencies were installed manually in smaller groups:

- common Python dependencies
- Kaolin
- Detectron2 from source
- hand-object detector extension
- PyTorch3D from source
- Chumpy
- MMPose / MMEngine
- HaMeR ViTPose
- rembg[gpu]
- NumPy / diffusers / transformers / HuggingFace Hub pins

## Decision criterion

Phase 0.7 is considered passed only after the final import check succeeds for the important packages:

- torch
- torchvision
- kaolin
- pytorch3d
- diffusers
- transformers
- trimesh
- cv2
- scipy
- skimage
- rembg
- smplx
- mmcv
- mmpose
- detectron2
- google.generativeai

## Next step

After Phase 0.7 repair passes, proceed to Phase 0.8:

- fetch bundled weights/data
- verify HaMeR / WiLoR downloaded assets  
