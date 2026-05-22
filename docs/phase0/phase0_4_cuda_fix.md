# Phase 0.4 — CUDA Toolkit Fix

## Goal

Fix the CUDA toolkit mismatch before creating the FollowMyHold `foho` environment.

## Previous problem

The NVIDIA driver supported CUDA 12.6, but the default CUDA compiler was CUDA 11.1:

/usr/local/cuda-11.1/bin/nvcc

Also, `/usr/local/cuda` pointed to CUDA 11.1.

## Fix

CUDA Toolkit 12.4 was installed, and `/usr/local/cuda` was repointed to:

/usr/local/cuda-12.4

## Verified result
which nvcc
# /usr/local/cuda/bin/nvcc

nvcc --version
# Cuda compilation tools, release 12.4, V12.4.131

readlink -f /usr/local/cuda
# /usr/local/cuda-12.4

## CUDA compile test

A tiny CUDA program compiled and ran successfully:
Hello from CUDA kernel!

## Decision

Phase 0.4 passed. The system is ready to proceed to Phase 0.5 for Conda / Miniforge setup.  
