# Phase 0.1 — Repo Snapshot

## Status

- Repository path: `/home/fredcui/Projects/FollowMyHold`
- Official remote: `https://github.com/aidilayce/FollowMyHold.git`
- Working branch for reproduction: `phase0-followmyhold-setup`
- Main purpose: reproduce FollowMyHold before adding HOLDSE-Flow contact verification modules.

## Expected repo structure confirmed

- `app.py`
- `assets/`
- `configs/`
- `scripts/`
- `src/`
- `test_splits/`
- `third_party/`
- `third_party_patches/`

## Important setup notes from README

- Hunyuan3D-2 must be cloned externally into `third_party/Hunyuan3D-2`.
- Hunyuan3D-2 must be checked out at commit `e664e7471642c09921d23baaeba8ebe79bd6c48b`.
- FollowMyHold patches must replace Hunyuan3D-2 `pipelines.py` and `schedulers.py`.
- Main environment name: `foho`.
- Main Python version: `3.10`.
