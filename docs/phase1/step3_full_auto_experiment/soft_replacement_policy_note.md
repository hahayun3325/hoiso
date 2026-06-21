# Soft replacement policy note

## Decision

We do not use selector-v4 as a final physical-validity judge.

Instead, selector-v4.1 chooses the best candidate for the next stage. Penetration depth is treated as a warning and as a target for later contact-aware optimization.

## Replacement meaning

At this stage, "replacement" means:

- copy the selected candidate into a soft-selected output folder;
- attach warning labels;
- pass the selected candidate to contact-aware optimization.

It does not mean the output is final paper-ready geometry.

## Why this is useful

This separates two problems:

1. candidate selection and object coherence;
2. physical contact correction.

The first is handled by selector-v4.1.
The second is handled by the future contact-aware optimization module.
