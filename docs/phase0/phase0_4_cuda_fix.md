# Phase 0.4 — CUDA Toolkit Fix

## Goal

Fix the CUDA toolkit mismatch before creating the FollowMyHold `foho` environment.

## Previous problem

The NVIDIA driver supported CUDA 12.6, but the default CUDA compiler was CUDA 11.1:


/usr/local/cuda-11.1/bin/nvcc

and /usr/local/cuda pointed to CUDA 11.1.

## Target

Use CUDA Toolkit 12.4 for FollowMyHold environment setup:

/usr/local/cuda -> /usr/local/cuda-12.4
nvcc --version -> release 12.4

## Reason

FollowMyHold installs PyTorch 2.5.0 + CUDA 12.4 and builds native CUDA-related extensions, including hand-object detector extensions and PyTorch3D.
