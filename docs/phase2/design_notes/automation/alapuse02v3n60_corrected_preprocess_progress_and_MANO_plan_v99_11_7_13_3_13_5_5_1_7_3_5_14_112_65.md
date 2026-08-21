# alapuse02v3n60 corrected preprocessing progress and selected-hand MANO plan

## Scope and status

Branch: `phase-2.1-agile-vlm-upstream-gate`  
Audited repository head when written: `ad8b58ee837c2809bfdf90934f1976bec0777d7c`  
Case: `alapuse02v3n60`  
Fresh lineage documented here: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_65`

Status: **preprocessing stage complete (1/7 foundation stages in this lineage)**.

`foundation_stage_closed` proves that `get_hunyuan_input` ran with the cached
Q0 packet, scalar object label `laptop`, fixed hand prompt `only hand`, and
resolved spatial owner `upper_image_hand`.  It does not claim that the other
six foundation stages, Q1/Q2, Gate A, optimization, or metrics are complete.

## Accepted receipts and hashes

- Stage receipt: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_65/foundation/controller/00_get_hunyuan_input/stage_receipt.json`
- Stage receipt SHA-256: `7139d2c2dfaa6d27933ff52ebadd4466c8c56f640648629801ddd2f38c8fd0c4`
- Stage inventory: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_65/foundation/outputs/01_preprocess/stage_inventory.json`
- Stage inventory SHA-256: `e6c313549f821890f8279ebaf73241fa3a429effbc4d64b3f124b110682e1827`
- Accepted Q0 packet: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_58/q0/combined_Q0_semantic_packet.json`
- Accepted Q0 SHA-256: `7fe45aa3e9319dd7de0a8c4107b4e5b2e1f475e7d243bab27fe936017c1031e4`
- Accepted input crop: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_hand_anchor/v99_11_7_hand_anchor_gate_policy/sequential_reanchor_collection_v99_11_7_9/indexed_identity_critic_v99_11_7_9_12/one_blind_v3_scope_authorization_v99_11_7_9_14/one_blind_v3_launch_policy_v99_11_7_9_15/v3_crop_source_recovery_v99_11_7_9_15_1/one_blind_v3_execution_v99_11_7_9_16/wrong_source_and_output_contract_recovery_v99_11_7_9_16_1/binary_reader_and_target_provenance_recovery_v99_11_7_9_16_1_1/corrected_target_replacement_launch_v99_11_7_9_16_2_1/input/v3_cropped_hoi/alapuse02v3n60_cropped_hoi_1.png`
- Accepted input SHA-256: `05c3dd582f0e499598c7eb6cf1088dca55af90672f8107d56530eb85c6887b20`

## Fresh preprocessing assets

- Cropped HOI: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_65/foundation/outputs/01_preprocess/cropped/alapuse02v3n60_cropped_hoi_0.png`
- Object mask: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_65/foundation/outputs/01_preprocess/masks/alapuse02v3n60_cropped_obj_mask.png`
- Hand mask: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_65/foundation/outputs/01_preprocess/masks/alapuse02v3n60_cropped_hand_mask.png`
- Object-only/inpainting input: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_65/foundation/outputs/01_preprocess/occ/alapuse02v3n60_occ_obj.png`
- Background-free HOI: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_65/foundation/outputs/01_preprocess/cropped_without_background/alapuse02v3n60_cropped_hoi_wo_bckg_0.png`
- Evidence panel: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_71/panels/alapuse02v3n60_preprocess_evidence_panel.png`
- Evidence-panel SHA-256: `467b092ff78dbc3e6dc7f44810205d4312ac2e727eb03790ddcc615ef57d6a23`
- Evidence sidecar: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_71/panels/alapuse02v3n60_preprocess_evidence_panel.json`

## Important installed scripts

- Front runner: `/home/fredcui/Projects/FollowMyHold/src/foho/automation/case_runner.py`
- Manifest builder: `/home/fredcui/Projects/FollowMyHold/src/foho/automation/foundation_manifest.py`
- GPU binder: `/home/fredcui/Projects/FollowMyHold/src/foho/automation/foundation_gpu_bind.py`
- Process controller: `/home/fredcui/Projects/FollowMyHold/src/foho/automation/foundation_process_controller.py`
- Conda child adapter: `/home/fredcui/Projects/FollowMyHold/src/foho/automation/foundation_run_in_conda_adapter.py`
- Preprocessing wrapper: `/home/fredcui/Projects/FollowMyHold/src/foho/preprocess/get_hunyuan_input.py`
- Segmentation owner: `/home/fredcui/Projects/FollowMyHold/src/foho/preprocess/segment_hoi_sam2.py`
- Legacy MANO owner (to be replaced): `/home/fredcui/Projects/FollowMyHold/src/foho/alignment/mano.py`
- Deterministic MANO geometry helper: `/home/fredcui/Projects/FollowMyHold/src/foho/automation/mano_geometry_gate.py`
- Bounded CPU 7-DoF replacement: `/home/fredcui/Projects/FollowMyHold/tools/gate_c_v99_11_hand_anchor/run_v3_CPU_7DoF_global_hand_alignment_v99_11_7_13_3_6.py`
- Independent ViTPose target extractor: `/home/fredcui/Projects/FollowMyHold/tools/gate_c_v99_11_hand_anchor/extract_case_image_vitpose_target_v99_11_7_9_21_7_2.py`

## Runtime variables

- `PROJECT_ROOT=/home/fredcui/Projects/FollowMyHold`
- `PHASE0_ROOT=/home/fredcui/foho_phase0`
- `CASE_ROOT=/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2`
- `PYTHON_BIN=/home/fredcui/anaconda3/envs/foho/bin/python`
- `SEG65_ROOT=/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_65`
- `ACCEPTED_Q0=/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_58/q0/combined_Q0_semantic_packet.json`
- `CASE_CONFIG=/home/fredcui/Projects/FollowMyHold/config/automation/alapuse02v3n60_case_runner_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_64.json`
- `CUDA_VISIBLE_DEVICES=0` only for explicitly launched GPU children.
- `OPENAI_API_KEY` is not read or printed in this stage.

## Hand identity and MANO policy

`upper_image_hand` is a spatial instance, not a handedness label.  The current
crop suffix is `0`.  Installed preprocessing
mirrors a detected left hand before cropping but historically preserves the
old class in the filename, while HaMeR later reads that suffix.  Before MANO
registration, the pipeline must write an explicit receipt containing source
instance, detector handedness, whether pixels were mirrored, canonical crop
handedness, selected HaMeR side, and independent ViTPose side.

No left- or right-specific case restriction is allowed.  Both ViTPose hand
candidates are compared to the selected hand mask; one unique match is
required.  A left source is canonicalized exactly once.  The selected raw
HaMeR mesh is registered with one bounded global scale, SO(3), and translation
against 2D keypoints plus MoGe hand support.  MANO articulation, shape, and
topology remain frozen.

## Remaining work

1. Run inpainting, MoGe, Hunyuan, HaMeR, and H2M from this accepted inventory;
   keep legacy MANO registration disabled.
2. Close original-versus-canonical handedness and rerun HaMeR if the suffix is
   inconsistent with the mirrored crop.
3. Bind all six fresh inputs of the bounded CPU 7-DoF registration.
4. Require topology, finite geometry, bounded scale, positive depth,
   reprojection, mask support, and a multi-view render to pass.
5. Make Q2 terminal and round-aware; obtain one true `READY_FOR_GATE_A` state.
6. Install post-Q2 Gate-A/frame-I/D0/H0/H1/O0/J0/F0/evaluation adapters.

Historical accepted J0/F0 assets are regression oracles only.  They are not
claimed as outputs of this fresh automatic lineage.
