# Phase 0.16 — Evaluation Script Findings

## Main finding

The repository contains official-style test split CSV files, but the current inspection did not find a complete project-specific official evaluation script.

## Test splits found

- `test_splits/dexycb_test.csv`
- `test_splits/arctic_test.csv`
- `test_splits/oakink_test.csv`

## Split sizes from current repository

1001 lines: arctic_test.csv
1001 lines: dexycb_test.csv
904 lines: oakink_test.csv

Since each file has a header, this corresponds to:

1000 ARCTIC samples1000 DexYCB samples903 OakInk samples

## Official metric protocol from paper/supplement

The official evaluation reports:

- Chamfer Distance (CD)
- F5
- F10
- Intersection Volume (I.V.)
- Reconstruction Rate (R.R.)

The supplement states:

- CD is computed using 30K sampled points.
- The reconstructed hand is first aligned to the ground-truth hand using ICP over scale, rotation, and translation.
- The same transform is applied to the reconstructed object.
- Object metrics are computed after this hand-based alignment.
- I.V. is computed using trimesh with 0.5cm voxel size.
- R.R. is the fraction of test samples where the method produces an output.

## Interpretation

The evaluator likely needs to be reconstructed from the paper/supplement unless an official script is found elsewhere.

## Next step

Build a minimal evaluator for one sample first, then extend to a small panel.  
