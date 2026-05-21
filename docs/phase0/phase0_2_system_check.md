# Phase 0.2 — System / GPU / CUDA / Disk Check

## Good signs

- OS: Ubuntu 22.04.5 LTS
- Kernel: Linux 6.8.0-111-generic
- GPU: NVIDIA GeForce RTX 4090
- VRAM: about 24GB
- NVIDIA driver: 560.35.03
- Driver CUDA support: 12.6
- `/home` disk: about 1.3T available
- `/home` inode usage: about 3%

## Main issue

The default CUDA compiler is currently CUDA 11.1:

```bash
/usr/local/cuda-11.1/bin/nvcc
and `/usr/local/cuda` points to CUDA 11.1.

This is risky because FollowMyHold expects a CUDA 12.x setup, especially for PyTorch 2.5.0 + cu124 and native extension builds.

## Decision

- Safe to proceed to Phase 0.3: install system dependencies.
- Do not run full `scripts/create_env_foho.sh` until CUDA toolkit is fixed.  
