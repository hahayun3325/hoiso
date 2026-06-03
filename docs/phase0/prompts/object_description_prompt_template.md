# Object Description Prompt Template

## Goal

Generate an object description for HOI reconstruction, not a generic caption.

The prompt should help 2D inpainting and 3D reconstruction preserve the correct object shape.

## Prompt to use

Describe the held object for 3D reconstruction.

Return **one concise sentence within 45 words** with these fields:

1. category
2. brand/text if visible
3. overall 3D shape
4. flat/round surfaces
5. visible silhouette
6. edges/corners
7. material/color if useful
8. negative shape constraint: what it is not

Do not describe the person or hand.
Focus only on the object geometry.

## CLIP prompt-length note

The inpainting model uses a CLIP-style text encoder.

The practical limit is **77 tokens**, not 77 words.

A token can be a full word, part of a word, punctuation, or a special token.

The pipeline may append extra text such as:

`, and preserve the image context.`

Therefore, 45 words is safer than 55 words.

## Example output

A rectangular SPAM canned meat tin with visible SPAM text, a boxy rounded-rectangular metal body, flat front and back faces, rounded corners, and blue-yellow printed surface; it is not a cylindrical can, bottle, or cup.

## Manual LLM query

Describe the held object for 3D reconstruction.

Return one concise sentence within 45 words with these fields:
1. category
2. brand/text if visible
3. overall 3D shape
4. flat/round surfaces
5. visible silhouette
6. edges/corners
7. material/color if useful
8. negative shape constraint: what it is not

Do not describe the person or hand.
Focus only on the object geometry.
