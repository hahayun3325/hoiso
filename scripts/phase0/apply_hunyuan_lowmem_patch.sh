#!/usr/bin/env bash
set -euo pipefail

cd /home/fredcui/Projects/FollowMyHold

cp third_party_patches/hy3dgen/shapegen/pipelines.py \
   third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py

python -m py_compile third_party/Hunyuan3D-2/hy3dgen/shapegen/pipelines.py

echo "[OK] applied Hunyuan low-memory octree patch"
