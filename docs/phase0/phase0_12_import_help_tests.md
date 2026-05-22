# Phase 0.12 — Import and Help Tests

## Goal

Run lightweight checks before launching the full FollowMyHold smoke test.

## Checks

- FollowMyHold source imports.
- `python -m foho.main --help`.
- `python app.py --help`.
- Local config sanity check.

## Decision

If all checks pass, proceed to Phase 0.13: first smoke-test inference.
