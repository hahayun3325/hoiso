# Phase 0.6 — Hunyuan3D-2 Clone and FollowMyHold Patches

## Goal

Clone Hunyuan3D-2 into `third_party/Hunyuan3D-2`, checkout the commit required by FollowMyHold, and apply the FollowMyHold patches.

## Required Hunyuan3D-2 commit

e664e7471642c09921d23baaeba8ebe79bd6c48b

## Required patch files

FollowMyHold patch files were copied into Hunyuan3D-2:
third_party_patches/hy3dgen/shapegen/pipelines.py
-> third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py

third_party_patches/hy3dgen/shapegen/schedulers.py
-> third_party/Hunyuan3D-2/hy3dgen/shapegen/schedulers.py

## Important note

`third_party/Hunyuan3D-2` is ignored by GitHub backup because it is an external dependency. Only setup notes and small reproducibility documentation are pushed to GitHub.

## Decision

After this phase, the machine is ready for Phase 0.7:

- create the `foho` conda environment
- install PyTorch 2.5.0 + CUDA 12.4
- build native extensions
- install FollowMyHold dependencies  
