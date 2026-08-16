# Automatic contact-patch radius selection and phase-config loading

Generated: 2026-08-16T03:12:54.969472+00:00

## Responsibility split

Gate D0/VLM selects a semantic object region. The geometry selector chooses
the exact radius and face IDs. It does not ask a VLM to estimate metric mesh
support.

## Selection rule

For each connected radius candidate, compute patch precision as in-ROI pixels
divided by visible patch pixels. Compute relative in-ROI support as in-ROI
pixels divided by the maximum in-ROI support in the radius sweep. Require at
least 90% precision and 50% relative support, then choose the smallest feasible
radius. If none passes, return REVIEW_REQUIRED.

The prior whole-ROI denominator was invalid because the yellow ROI represents
possible overlap, not an exact contact target. For alapuse02v3n60, the corrected
rule selects r04.

## Project owners

- Selector: tools/hoiso_d0_objective_contract/select_contact_patch_radius.py
- Config loader: tools/hoiso_d0_objective_contract/phase_config_loader.py
- CPU tests: tests/hoiso_d0_objective_contract/test_selector_and_phase_loader.py

The loader validates schema, phase, PASS status, source hashes, and explicit
parameter names. The live runner must still map these names to its actual
tensors and prove gradient isolation before H0.

## Raster schedule

H0/H1 cache the raster because the object is frozen. O0/J0 rasterize once per
forward iteration from the current object, share that result across all loss
terms, then rerasterize after the next object update.
