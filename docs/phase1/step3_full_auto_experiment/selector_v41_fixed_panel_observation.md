# selector-v4.1 fixed panel observation

## Status

The fixed selector-v4.1 comparison panels were generated successfully.

The previous missing-image issue was caused by the panel script relying on unavailable pre-rendered images. The fixed script renders directly from real PLY mesh paths.

## Current panel meaning

The panels compare:

1. input image
2. baseline final HOI
3. selector + GPT-5.5 final HOI
4. selector-v4.1 soft-selected HOI
5. selector-v4.1 decision and warning tags

## Important limitation

This is not yet the final selector-v4.1 full-pipeline experiment.

The current selector-v4.1 result is a soft-selected candidate. The next experiment should rerun selector-v4.1 inside the pipeline using the refined prompt template, then evaluate the final HOI mesh.
