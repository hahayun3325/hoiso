# Phase 0.10 — Secrets and Model Cache

## Goal

Set local secrets and model cache paths for FollowMyHold.

## Local secrets file

Secrets are stored outside the repository:

~/.foho_secrets

This file contains:

HF_TOKENGEMINI_API_KEY, HY3DGEN_MODELSHF_HOME, HF_HUB_CACHE, TRANSFORMERS_CACHE, TORCH_HOME

## Cache paths

Model caches are stored under:

~/foho_phase0/cache/

## Safety

- `~/.foho_secrets` must not be committed to GitHub.
- API keys must not be printed into logs.
- Licensed assets such as MANO files must not be pushed to public repositories.

## Decision

After this phase, the machine is ready to create a Phase 0 smoke-test config.  
