# Manual LLM Query for Object Reconstruction Prompt

Use this exact query when asking an LLM to describe a held object.

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

## Why 45 words?

The inpainting model uses a CLIP-style text encoder with a practical limit of 77 tokens.

The pipeline may append extra text such as:

, and preserve the image context.

So 45 words is a safer practical limit than 55 words.  
