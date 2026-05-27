# Phase 0 Smoke Run Manifest

## Purpose

This document records the important Phase 0 smoke runs for FollowMyHold reproduction and prompt/semantic-drift analysis.

The goal is to record:

- run ID
- input case
- prompt type
- memory settings
- whether final files exist
- qualitative observation
- main lesson
- next action

---

## Input Case

Dataset: HO3D v3  
Split: train  
Likely sequence: GPMF13  
Likely frame: 0873  
Object: SPAM canned meat tin  

Important note: the object is a rectangular / boxy SPAM tin with rounded rectangular corners, not a generic cylindrical can.

---

## Run Summary

| Run | Prompt / Input Condition | Main Memory Setting | Final Output | Quality Observation | Main Lesson |
|---|---|---|---|---|---|
| smoke_013 | Gemini baseline: `A can of Spam.` | Low-memory guidance, final octree around 192 | Passed | Final object became a rounded generic can | Vague object prompt can cause semantic drift |
| smoke_015 | Structured rectangular SPAM prompt | Full-ish guidance attempt | Failed final guidance due to OOM | Inpaint and Hunyuan initial mesh preserved boxy SPAM shape | Structured prompt improves 2D inpainting and initial 3D shape |
| smoke_016 | Structured prompt, reused smoke_015 intermediates | Ultra-low guidance, `FOHO_FINAL_OCTREE_RES=128` | Passed | Final object completed but became fragmented / incomplete | Ultra-low memory can finish but hurts final object detail |
| smoke_017 | Structured prompt, reused smoke_015 intermediates | Better low-memory guidance, `FOHO_FINAL_OCTREE_RES=192` | Passed | Higher density than smoke_016, but final object is still incomplete | Object degradation is not caused by octree resolution alone |

---

## smoke_013

Prompt:

A can of Spam.

Observation:

The run completed and produced final meshes. The hand-object pose was plausible, but the object became a rounded generic can.

Lesson:

The prompt was semantically correct but geometrically vague. This likely caused semantic drift.

---

## smoke_015

Prompt:

`A rectangular SPAM canned meat tin with flat front and back faces, rounded rectangular corners, and a metal top. The object is boxy and not a cylindrical soda can or soup can.`

Observation:

The inpainted object and Hunyuan initial mesh preserved the boxy SPAM shape. However, final guidance hit CUDA OOM.

Lesson:

Structured prompting improves semantic object recovery, but final guidance still needs memory control.

---

## smoke_016

Key settings:

`FOHO_NUM_INFERENCE_STEPS=6FOHO_OPT_STEPS_HAND=20FOHO_OPT_STEPS_SCALE=10FOHO_OPT_STEPS_JOINT=5FOHO_FINAL_OCTREE_RES=128`

Observation:

The run completed, but the final object was fragmented / incomplete.

Lesson:

Ultra-low guidance can complete, but damages object quality.

---

## smoke_017

Key change:

`FOHO_FINAL_OCTREE_RES=128 -> 192`

Observation:

The run completed and produced denser final meshes than smoke_016. However, the final object is still incomplete.

Lesson:

Increasing final octree resolution improves density but does not fully recover the object. The remaining issue may be guidance optimization, object extraction, coordinate transform, or mesh separation.

---

## Current Research Conclusion

Vague object descriptions can produce geometrically plausible but semantically incorrect object reconstruction.

Structured object prompts can preserve object identity better at the inpainting and initial 3D generation stages.

However, final guidance quality depends strongly on memory settings and may degrade object completeness.

This supports the HOLDSE-Flow direction:

- structured MLLM prompting
- semantic drift diagnosis
- mask-inpaint consistency checking
- 2D-3D consistency verification
- confidence-guided coordination
- contact-aware physical refinement

---

## Next Action

Before moving to official evaluation scripts, inspect why the smoke_017 final object is still incomplete:

1. render final hand-object scene,
2. check connected components,
3. compare Hunyuan initial mesh vs final object,
4. check whether final object extraction is damaging geometry.  
