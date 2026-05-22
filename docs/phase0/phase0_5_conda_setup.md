# Phase 0.5 — Conda / Environment Tool Setup

## Goal

Prepare Conda/Anaconda and persistent CUDA environment variables before creating the FollowMyHold `foho` environment.

## Conda status

Conda is available from the existing Anaconda installation:

/home/fredcui/anaconda3/bin/conda

The correct `CONDA_SH` path is:

`/home/fredcui/anaconda3/etc/profile.d/conda.sh`

## Required variables
export CONDA_SH="$HOME/anaconda3/etc/profile.d/conda.sh"
export CUDA_HOME="/usr/local/cuda"

## CUDA status

CUDA Toolkit 12.4 is active:
/usr/local/cuda -> /usr/local/cuda-12.4
nvcc --version -> release 12.4

## Decision

Phase 0.5 passed after correcting the Conda path from the missing Miniforge path to the existing Anaconda path.

The machine is ready for Phase 0.6:

- clone Hunyuan3D-2
- checkout the required commit
- apply FollowMyHold patches  
