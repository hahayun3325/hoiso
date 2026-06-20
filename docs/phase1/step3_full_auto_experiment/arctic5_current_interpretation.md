# ARCTIC-5 current interpretation after selector-v4 metrics

## Main observation

The part-aware prompt rerun improves object geometry for `aket01`, but selector-v4 correctly rejects it because of severe hand-object penetration.

## Important interpretation

Selector-v4 should not be described as only "better object reconstruction." Its main role is:

1. reject bad original candidates;
2. trigger prompt-refined rerun;
3. evaluate the rerun using physical metrics;
4. accept only physically plausible outputs.

## aket01 result

The part-aware rerun improves object coherence and reduces floating. However, it introduces severe penetration, so it should be sent to attempt1 fallback or later contact-aware guidance.

## Next step

Proceed to ARCTIC-5 automatic comparison / rerun batch, not final full automatic replacement.
