# Phase 0.3 — Basic System Dependencies

## Status

Basic system dependencies were installed successfully.

## Verified tools

- `git`
- `git-lfs`
- `gcc`
- `g++`
- `cmake`
- `ninja`
- `ffmpeg`

## Verified versions

- Git: 2.34.1
- Git LFS: 3.0.2
- GCC: 10.5.0
- G++: 10.5.0
- CMake: 3.22.1
- Ninja: 1.10.1
- FFmpeg: 4.4.2

## Backup status

- GitHub remote `hoiso` was added.
- Branch `phase0-followmyhold-setup` was pushed to `git@github.com:hahayun3325/hoiso.git`.
- Hugging Face repo `hahayun/hoiso` exists.
- Phase 0 logs were uploaded to Hugging Face.

## Notes

The failed upload of `~/foho_phase0/runs/smoke_001` is expected because the smoke test has not been run yet.

## Next step

Proceed to Phase 0.4 to fix CUDA toolkit. The current default CUDA compiler is still CUDA 11.1, while FollowMyHold expects a CUDA 12.x setup.
