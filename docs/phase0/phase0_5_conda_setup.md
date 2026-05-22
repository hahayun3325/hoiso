# Phase 0.5 — Conda / Environment Tool Setup

## Goal

Prepare Conda/Miniforge and persistent CUDA environment variables before creating the FollowMyHold `foho` environment.

## Required variables

CONDA_SH="$HOME/miniforge3/etc/profile.d/conda.sh"
CUDA_HOME="/usr/local/cuda"

## CUDA status

CUDA Toolkit 12.4 is active:

/usr/local/cuda -> /usr/local/cuda-12.4
nvcc --version -> release 12.4

## Decision

After this phase, the machine is ready for Phase 0.6:

- clone Hunyuan3D-2
- checkout the required commit
- apply FollowMyHold patches  
