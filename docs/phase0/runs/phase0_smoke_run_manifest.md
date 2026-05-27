# Phase 0 Smoke Run Manifest

## Purpose

This document records the important Phase 0 smoke runs for FollowMyHold reproduction and prompt/semantic-drift analysis.

The goal is to record the run ID, input case, prompt type, memory settings, final-output status, qualitative observation, main lesson, and next action.

## Input Case

Dataset: HO3D v3  
Split: train  
Likely sequence: GPMF13  
Likely frame: 0873  
Object: SPAM canned meat tin  

The object is a rectangular / boxy SPAM tin with rounded rectangular corners, not a generic cylindrical can.

## Run Summary

| Run | Prompt / Input Condition | Main Memory Setting | Final Output | Quality Observation | Main Lesson |
|---|---|---|---|---|---|
| smoke_013 | Gemini baseline: `A can of Spam.` | Low-memory guidance, final octree around 192 | Passed | Final object became a rounded generic can | Vague prompt can cause semantic drift |
| smoke_015 | Structured rectangular SPAM prompt | Full-ish guidance attempt | Failed final guidance due to OOM | Inpaint and Hunyuan initial mesh preserved boxy SPAM shape | Structured prompt improves 2D inpainting and initial 3D shape |
| smoke_016 | Structured prompt, reused smoke_015 intermediates | Ultra-low guidance, `FOHO_FINAL_OCTREE_RES=128` | Passed | Final object became fragmented / incomplete | Ultra-low memory can finish but hurts final object detail |
| smoke_017 | Structured prompt, reused smoke_015 intermediates | Better low-memory guidance, `FOHO_FINAL_OCTREE_RES=192` | Passed | Denser than smoke_016, but still fragmented | Object degradation is not caused by octree resolution alone |

## Main Findings

1. The baseline prompt was semantically correct but geometrically vague.
2. The structured object prompt reduced semantic drift in the inpainting stage.
3. The Hunyuan initial mesh after structured prompting preserved the boxy SPAM shape.
4. Final object meshes from smoke_016 and smoke_017 became fragmented.
5. Increasing octree resolution from 128 to 192 improved mesh density but did not restore completeness.
6. The likely failure point is the final guidance / object-extraction stage.

## Research Implication

This supports the HOLDSE-Flow direction:

- structured MLLM prompting
- semantic drift diagnosis
- mask-inpaint consistency checking
- 2D-3D consistency verification
- object-completeness checking
- confidence-guided coordination
- contact-aware physical refinement

## Next Action

Inspect the final guidance / object-extraction stage and locate where the complete Hunyuan initial mesh becomes fragmented.
