# aket01 dry-run v1 guidance-frame final decision

## Decision

PASS_SHARED_FRAME.

## Evidence

The v1 scene uses:

- guidance_out/aket01_hand.ply
- guidance_out/aket01_obj.ply
- active parts from part_meshes_partfield_v3_vmap

The hand visually grips the bottle in a pose consistent with the cropped input image.

The numeric report also supports this:

- hand_to_guidance_object min distance is about 0.002 m
- hand_to_guidance_object p10 is about 0.0094 m
- hand_to_active_parts is very similar
- guidance_object_to_active_parts is tightly aligned

## Interpretation

The v0 floating-hand issue was caused by mixing coordinate families.

No root-correction pass is needed for aket01 before Gate C.

## Next step

Run Gate C v0 contact verification on guidance_out hand + active parts.

Expected semantic contact:

- main contact: bottle body
- possible secondary contact: top/neck/cap only if geometry supports it
- residual_uncertain should not be used as a primary semantic contact target
