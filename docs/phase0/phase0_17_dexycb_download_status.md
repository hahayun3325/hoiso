# Phase 0.17 — DexYCB Download Status

## Current issue

The first full DexYCB archive download failed because Google Drive blocked the shared 119G file with a quota message.

The first subject-wise terminal download also failed because the downloaded `.tar.gz` files were only about 68K and were not valid gzip archives. These files were Google Drive HTML pages saved with `.tar.gz` names.

## Resolution

The retry script using direct Google Drive file IDs successfully downloaded valid archives:

20200709-subject-01.tar.gz
calibration.tar.gz
models.tar.gz

All three passed gzip/tar validation and were extracted successfully.

## Current readiness

The flexible split resolver now finds the first 10 DexYCB split images.

Current official dataset image readiness:

DexYCB: 10/10 found for subject-01 subsetARCTIC: 10/10 foundOakInk: 10/10 found

## Important note

Only subject-01 is available for DexYCB right now. This is enough for Phase 0.17 mini testing, but not enough for full official evaluation.
