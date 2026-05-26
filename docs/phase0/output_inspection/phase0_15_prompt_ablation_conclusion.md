# Phase 0.15 — Prompt / Semantic-Drift Ablation Conclusion

## Status

Phase 0.15 passed.

## Main finding

The structured rectangular SPAM prompt reduced semantic drift.

The baseline Gemini response was:

A can of Spam.

Final outputs were produced:

- `guidance_out/test_obj.ply`
- `guidance_out/test_hand.ply`

## Important limitation

smoke_016 is a low-memory qualitative test, not a paper-quality setting.

The result should be used to support the semantic-drift diagnosis and structured-prompting direction, not as a direct quantitative comparison with the official FollowMyHold paper.

## Research implication

This supports the HOLDSE-Flow direction:

- structured MLLM prompting
- semantic drift diagnosis
- mask-inpaint consistency checking
- 2D-3D silhouette verification
- confidence-guided coordination
- contact-aware physical refinement  
