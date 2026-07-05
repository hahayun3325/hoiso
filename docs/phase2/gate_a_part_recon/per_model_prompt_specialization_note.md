# Why different foundation models need different prompts

## What happened (alapuse02_v3 case study)

The same 45-word geometry-rich reconstruction prompt (designed for FLUX
inpainting + object naming) was reused as the SAM2/LangSAM segmentation
prompt. Result: SAM2 segmented the wrong object (a support box) instead
of the laptop, while FLUX correctly inpainted a laptop from the same text.
Root cause confirmed via controlled A/B test: switching only the
segmentation prompt to a 4-word direct phrase ("open toy laptop screen
keyboard") fixed the mask, with every other pipeline input unchanged.

## Why this happens

- FLUX / Hunyuan3D: diffusion generative models with text encoders trained
  on long, descriptive captions. They benefit from rich detail: category,
  parts, material, negative constraints.
- SAM2 / LangSAM: the language-grounding component is a phrase-grounding
  detector (referring-expression style), trained mainly on short, direct
  noun phrases. Long compound descriptions with multiple clauses and
  negative constraints can dilute attention or cause it to fixate on the
  wrong sub-phrase — especially risky when a negative constraint
  (e.g. "not a box") mentions a real nearby distractor object by name.

## Rule of thumb going forward

Different pipeline stages need prompts written for what that specific
model was trained on, not one shared "master description":

| Stage | Model type | Prompt style |
|---|---|---|
| Object naming / reconstruction guidance | Gemini / GPT-5.5 (LLM) | Long, structured, geometry-rich (see manual_object_prompt_query_45_words.md) |
| Inpainting | FLUX (diffusion, text-conditioned) | Same long prompt works well |
| Object segmentation | SAM2 / LangSAM (phrase-grounding) | Short, direct noun phrase, 2-6 words, NO negative constraints, avoid naming distractor objects |

## Early-warning signal for next time

If a new case's cropped_obj_mask.png doesn't visually match the target
object, check the segmentation prompt FIRST, before suspecting Hunyuan,
MoGe, or the optimizer. The mask is upstream of all 3D geometry; nothing
downstream can be trusted until the mask is confirmed correct by eye.

## Related literature

- FollowMyHold's own paper documents this exact failure class as a known
  limitation: upstream segmentation/inpainting errors propagate to
  reconstruction (their reported failure case: incorrect inpainting led
  to reconstructing two cans instead of the intended object).
- AGILE (2026) addresses this with a VLM-guided verification/rejection
  step between generation and 3D lifting, rather than trusting the first
  segmentation/generation pass.
