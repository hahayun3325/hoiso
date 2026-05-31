# Phase 0.17 — DexYCB Download Status

## Current issue

The first full DexYCB archive download failed because Google Drive blocked the shared 119G file with a quota message:

Too many users have viewed or downloaded this file recently.
This is not a local environment error.

## Resolution plan

Use the official subject-wise DexYCB downloads instead of the full archive.

For Phase 0.17 mini testing, only the first subject is needed first:

20200709-subject-01.tar.gzcalibration.tar.gzmodels.tar.gz

After extraction, the dataset root should contain:

20200709-subject-01/calibration/models/

## Next action

Run `scripts/phase0/download_dexycb_subjectwise.py minimal`.  
