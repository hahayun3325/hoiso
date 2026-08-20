# TraceHOI ARCTIC-1000 Luna open-state classification

## Scope

This is a reproducible candidate-selection record, not benchmark ground truth. Luna evaluated 234 priority `use` images from four articulated categories; it did not classify every ARCTIC-1000 row.

## Query contract

- Model: `gpt-5.6-luna`; reasoning effort: `none`; response storage: disabled.
- Input: 27 case-owned 3-by-3 panels containing 234 cells.
- Output per exact cell: `case_id`, `OPEN|CLOSED|UNCERTAIN`, confidence, and visible evidence.
- Accepted total cost: `$0.0269658`; failed attempts: `0`.

## Results

| State | Count |
|---|---:|
| OPEN | 110 |
| CLOSED | 114 |
| UNCERTAIN | 10 |
| Total | 234 |

| OPEN category | Count |
|---|---:|
| laptop | 34 |
| microwave | 28 |
| notebook | 24 |
| scissors | 24 |

Native `obj_arti` is available for 233 of 234 classified rows. It is metadata, not the visual label.

## OPEN subset

- Root: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/arctic_open_articulated_subset_v99_11_7_13_3_13_5_5_1_7_3_5_14_113_6`.
- JSON manifest: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/arctic_open_articulated_subset_v99_11_7_13_3_13_5_5_1_7_3_5_14_113_6/reports/open_articulated_subset_manifest.json`.
- CSV review sheet: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/arctic_open_articulated_subset_v99_11_7_13_3_13_5_5_1_7_3_5_14_113_6/reports/open_articulated_subset_manifest.csv`.
- SHA-256 list: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/arctic_open_articulated_subset_v99_11_7_13_3_13_5_5_1_7_3_5_14_113_6/reports/SHA256SUMS.txt`.
- The 110 images were copied, not moved; ten UNCERTAIN rows were excluded.

## Reproducibility owners

- `LABELS_ANGLE_CSV`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/arctic_open_state_review_v99_11_7_13_3_13_5_5_1_7_3_5_14_113_5/reports/open_state_labels_with_obj_arti.csv` — `350603d33e7f36038ae831adb1ef023cf5cee59af71b94f5db5219e45806ecbf`
- `LUNA_PROMPT`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/arctic_open_state_review_v99_11_7_13_3_13_5_5_1_7_3_5_14_113_5/open_state_visual_label_prompt_cell_owned.txt` — `a6b2aa6aa2e951ac2d49ad5af2150958a70f9928cdd7665bace91e75102a553f`
- `LUNA_RUNNER`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/arctic_open_state_review_v99_11_7_13_3_13_5_5_1_7_3_5_14_113_5/query_open_state_panels_cell_owned_luna.py` — `031bf5b31f627388840ecf31d9fe6ff8b43355309ef0d736982a7d39cdf433b5`
- `LUNA_TEST`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/arctic_open_state_review_v99_11_7_13_3_13_5_5_1_7_3_5_14_113_5/test_query_open_state_panels_cell_owned_luna.py` — `3cb56f24c8b7c998905ddb909f71831005bec8afa56ee8b5530ec0971d22511f`
- `OPEN_SUBSET_CSV`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/arctic_open_articulated_subset_v99_11_7_13_3_13_5_5_1_7_3_5_14_113_6/reports/open_articulated_subset_manifest.csv` — `cff3d6c3a317fdd81cbc55f4f04aa08aa4148509f8e126fe3aeacfb633fbd69b`
- `OPEN_SUBSET_HASHES`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/arctic_open_articulated_subset_v99_11_7_13_3_13_5_5_1_7_3_5_14_113_6/reports/SHA256SUMS.txt` — `c766e7e35579156dc7b4ccda1b4042ce0dc34ab339711fd617c5b34477832b17`
- `OPEN_SUBSET_INDEPENDENT_AUDIT`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/arctic_open_articulated_subset_v99_11_7_13_3_13_5_5_1_7_3_5_14_113_6/reports/open_articulated_subset_independent_audit.json` — `5169d373e4f97b53a999d5bcb7e14864b51b05b08d2c5003cc23308d38d02b4e`
- `OPEN_SUBSET_MANIFEST`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/arctic_open_articulated_subset_v99_11_7_13_3_13_5_5_1_7_3_5_14_113_6/reports/open_articulated_subset_manifest.json` — `d3a16cb1bf8cae6a8a146cdc1aa0faf4945c80aaa13eebd286083973c3485b51`
- `OPEN_SUBSET_WRITE_AUDIT`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/arctic_open_articulated_subset_v99_11_7_13_3_13_5_5_1_7_3_5_14_113_6/reports/open_articulated_subset_write_audit.json` — `5f2a52ca04d1d7fa56895e5400f7a33b62f9ad96a37870e6e3fc7c3c60858f67`
- `PANEL_AUDIT`: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/arctic_open_state_review_v99_11_7_13_3_13_5_5_1_7_3_5_14_113_5/reports/open_state_full_classification_audit.json` — `bada95cc5a7914ef9e42ddb6ee44788e2252b767e28f38ebffd5d52f8ea01e21`

## Limitations

These labels screen cases for later reconstruction. They do not measure alignment, object pose, hand pose, or F0. A blind human audit must be recorded before a paper subset is frozen.
