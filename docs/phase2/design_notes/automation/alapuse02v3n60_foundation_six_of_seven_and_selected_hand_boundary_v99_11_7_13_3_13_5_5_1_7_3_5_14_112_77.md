# alapuse02v3n60 fresh foundation progress: six of seven stages

## Status

The fresh `14_112_65` lineage has completed preprocessing, inpainting, MoGe,
Hunyuan object reconstruction, HaMeR hand estimation, and H2M. Legacy MANO
registration was intentionally not launched. Q1/Q2 and post-Q2 optimization
are not outputs of this lineage.

## Inventory hashes

- `01_preprocess`: `e6c313549f821890f8279ebaf73241fa3a429effbc4d64b3f124b110682e1827`
- `02_inpaint`: `b92620d0b7baca2d51cbc49274c93d9b5187a417de8e3e5aead0acfb3aac5c48`
- `03_hamer`: `934adb23b017a8a3f50f59a83e8b87317893695aa56112fb8edb62a86eafc146`
- `04_moge`: `596da0d07d9856cc3e2f8579bc532d58bb70906d9ca1fe39a2c458562125a5fd`
- `05_hunyuan`: `1bd0ed9b03839b888708a8e9faa6813d4a904d06c016256af649aaad51190a57`
- `06_h2m`: `6b81fd84fdf5cd8e19f7a18d7ca320d43df5e1d13a3238e1d9a72eaf8d118704`

## Important assets

- Lineage: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_65`
- Preprocess panel: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_71/panels/alapuse02v3n60_preprocess_evidence_panel.png`
- Q0 packet: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_58/q0/combined_Q0_semantic_packet.json`
- Descendant controller: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_65/foundation/controller_descendants_2_to_6/controller_result.json`
- Stage outputs: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_65/foundation/outputs`

## Important source owners

- `src/foho/automation/case_runner.py`
- `src/foho/automation/foundation_process_controller.py`
- `src/foho/automation/foundation_manifest_rebind.py`
- `src/foho/preprocess/segment_hoi_sam2.py`
- `src/foho/preprocess/get_hunyuan_input.py`
- `src/foho/hand/hamer.py`
- `src/foho/automation/mano_geometry_gate.py`
- `tools/gate_c_v99_11_hand_anchor/run_v3_CPU_7DoF_global_hand_alignment_v99_11_7_13_3_6.py`

## Runtime variables

- `PROJECT_ROOT=/home/fredcui/Projects/FollowMyHold`
- `PHASE0_ROOT=/home/fredcui/foho_phase0`
- `CASE_ROOT=/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2`
- `SEG65_ROOT=/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_65`
- `PYTHON_BIN=/home/fredcui/anaconda3/envs/foho/bin/python`
- `CUDA_VISIBLE_DEVICES=0` only for an explicitly launched child.

## Remaining front-half boundary

The selected spatial hand, original detector side, mirror operation, canonical
crop side, selected HaMeR candidate, independent ViTPose target, CPU 7-DoF
registration, and geometry gate must close before a paid jury call. This is not
a left-only policy and does not authorize accepting an arbitrary visible hand.
