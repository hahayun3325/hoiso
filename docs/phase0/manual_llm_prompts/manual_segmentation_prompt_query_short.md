# Segmentation-specific prompt template (SAM2 / LangSAM)

## Purpose

This is a DIFFERENT prompt from the 45-word reconstruction/object-naming
template (manual_object_prompt_query_45_words.md). Do not reuse that
template for segmentation. This template is specifically for the
FOHO_SEGMENT_OBJECT_PROMPT override consumed by segment_hoi_sam2.py.

## Template

A short noun phrase, 2-6 words, naming ONLY the target object.

Rules:
1. No negative constraints ("not a box", "not a can") — naming a real
   nearby distractor object, even negatively, can pull the grounding
   model's attention toward it.
2. No compound/multi-clause descriptions.
3. No material, color, or brand detail unless it disambiguates from a
   visually similar distractor in the same frame.
4. If the object is mid-articulation (open/closed), a single state word
   is fine (e.g. "open"), but do not describe hinge mechanics.

## Worked example: alapuse02_v3

Reconstruction prompt (do NOT reuse for segmentation):
"A wooden toy laptop, articulated two-part object with a flat rectangular
screen panel hinged to a flat rectangular keyboard base, currently open
at an angle, light-tan wood surfaces with painted dark keyboard/screen
areas, not a book, box, tablet, or single rigid slab."

Segmentation prompt (correct, confirmed working):
"open toy laptop screen keyboard"

## Decision rule

Always visually inspect cropped_obj_mask.png against the actual target
object BEFORE trusting any downstream stage. If wrong, try a shorter,
more direct segmentation prompt via FOHO_SEGMENT_OBJECT_PROMPT before
suspecting Hunyuan/MoGe/optimizer issues.
