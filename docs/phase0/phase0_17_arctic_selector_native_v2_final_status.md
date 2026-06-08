# Phase 0.17 — ARCTIC Selector-Native v2 Final Status

## Goal

Run 3–5 official-dataset ARCTIC samples with GPT-5.5 prompt and automatic internal selector.

## Final status

The clean selector-native v2 runs now save outputs into the correct v2 folders.

For each case, the v2 folders contain:

- cropped HOI image
- inpainted object image
- selector-native before/after Phase 4.2 renders
- selector candidate PLYs
- final object mesh
- final hand mesh

## Panel

The final qualitative panel is:

`arctic_selector_native_v2_panel_clean.jpg`

This panel should be preferred over the earlier mixed-path panel because it reads from the v2 folders only.

## amicuse01 note

`amicuse01` is memory-sensitive. The standard octree-192 run failed during final extraction. The low-memory octree-128 run completed but produced degraded/collapsed object geometry.

This case should be reported separately as evidence that memory fallback alone is not enough; a confidence-guided object-preservation fallback is still needed.
