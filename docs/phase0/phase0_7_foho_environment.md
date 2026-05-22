# Phase 0.7 — Create the `foho` Environment

## Goal

Create the official FollowMyHold conda environment before fetching weights and running the pipeline.

## Environment setup

The environment was created using:

export CONDA_SH="$HOME/anaconda3/etc/profile.d/conda.sh"
export CUDA_HOME="/usr/local/cuda"
export TORCH_CUDA_ARCH_LIST="8.9"
export MAX_JOBS=8

bash scripts/create_env_foho.sh

## Expected core versions

Python: 3.10PyTorch: 2.5.0+cu124CUDA runtime used by PyTorch: 12.4CUDA toolkit: /usr/local/cuda -> /usr/local/cuda-12.4GPU: NVIDIA GeForce RTX 4090

## Important dependencies

The environment should include:

- PyTorch
- TorchVision
- Kaolin
- PyTorch3D
- Diffusers
- Transformers
- Detectron2
- HaMeR / ViTPose dependencies
- rembg
- SMPL-X
- OpenCV
- Trimesh

## Decision

After this phase, the machine is ready for Phase 0.8:

- fetch bundled weights/data
- download or place manual detector/MANO assets
- prepare the first smoke-test config  
