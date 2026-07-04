# aket01 Gate C v0 final decision

## Decision

PASS_BODY_CONTACT.

## Evidence

The contact verification script selected:

- best_part = body
- decision = PASS_BODY_CONTACT_CANDIDATE

The body contact statistics are strong:

- min distance ≈ 0.0026 m
- p5 ≈ 0.0064 m
- p10 ≈ 0.0085 m
- within_01 = 117
- within_02 = 373
- within_05 = 589

The non-primary parts are correctly rejected:

- residual_uncertain: within_05 = 0
- top_or_cap: within_05 = 0

## Visual interpretation

The hand is wrapped around the main bottle body. The contact markers are on the grasping fingers and the bottle body surface.

## Correction

Do not say residual_uncertain and top_or_cap have zero points within 0.5 m. The script proves zero points within 0.05 m / 5 cm.

## Next step

Run Gate D contact-aware scorer sandbox v0 using body contact as the verified target.
