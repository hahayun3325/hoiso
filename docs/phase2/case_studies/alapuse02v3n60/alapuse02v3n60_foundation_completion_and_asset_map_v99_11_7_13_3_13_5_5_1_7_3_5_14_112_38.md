# alapuse02v3n60 fresh foundation completion and asset map

- Foundation status: **COMPLETE (7/7 stage inventories closed)**
- Source commit: `28821d9c3346758cfc961ab3a4e4fb72fdbd001f`
- Runtime config: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/config/alapuse02v3n60_fresh_foundation_recovery.env`
- Executable manifest: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/config/alapuse02v3n60_fresh_foundation_recovery_manifest.json`
- Controller run root: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/controller_live`
- Fresh artifact root: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary`
- Foundation-pass OpenAI calls: **0**

## Accepted semantic owners

- Q0 packet: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_22/live_combined_Q0/combined_Q0_semantic_packet.json`
- Q0 audit: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_22/reports/terra_medium_live_Q0_audit.json`
- Five-consumer handoff: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_22/reports/five_foundation_consumer_handoff.json`
- Prompt packet: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_29_1/compatibility/five_Q0_prompt_values.json`
- Object prompt CSV: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_29_1/compatibility/object_segmentation_prompts.csv`
- Inpainting prompt CSV: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_29_1/compatibility/flux_inpainting_prompts.csv`
- Q1 policy: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_2/candidates/auto_v2_primary_and_recheck_jury_policy.json`

## Important implementation owners

- Controller: `/home/fredcui/Projects/FollowMyHold/src/foho/automation/foundation_process_controller.py`
- Conda/inventory adapter: `/home/fredcui/Projects/FollowMyHold/src/foho/automation/foundation_run_in_conda_adapter.py`
- Manifest builder: `/home/fredcui/Projects/FollowMyHold/src/foho/automation/foundation_manifest.py`
- MoGe wrapper: `/home/fredcui/Projects/FollowMyHold/src/foho/geometry/moge.py`

## Runtime variable contract

- `PROJECT_ROOT` = `/home/fredcui/Projects/FollowMyHold`
- `CONDA_SH` = `/home/fredcui/anaconda3/etc/profile.d/conda.sh`
- `ENV_NAME` = `foho`
- `ENV_PREFIX` = `/home/fredcui/anaconda3/envs/foho`
- `IMAGE_PATH` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/gate_c_hand_anchor/v99_11_7_hand_anchor_gate_policy/sequential_reanchor_collection_v99_11_7_9/indexed_identity_critic_v99_11_7_9_12/one_blind_v3_scope_authorization_v99_11_7_9_14/one_blind_v3_launch_policy_v99_11_7_9_15/v3_crop_source_recovery_v99_11_7_9_15_1/one_blind_v3_execution_v99_11_7_9_16/wrong_source_and_output_contract_recovery_v99_11_7_9_16_1/binary_reader_and_target_provenance_recovery_v99_11_7_9_16_1_1/corrected_target_replacement_launch_v99_11_7_9_16_2_1/input/v3_cropped_hoi/alapuse02v3n60_cropped_hoi_1.png`
- `BASE_DIR` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary`
- `ORIGINAL_IMG_DIR` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/01_preprocess/original`
- `MASKED_OBJ_PATH` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/01_preprocess/occ`
- `CROPPED_HOI_PATH` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/01_preprocess/cropped`
- `CROPPED_HOI_WO_BCKG_PATH` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/01_preprocess/cropped_without_background`
- `MASK_DIR_PATH` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/01_preprocess/masks`
- `CROPPED_INPAINTED_OBJ` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/02_inpaint`
- `HAMER_OUT_PATH` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/03_hamer`
- `MOGE_OUT_PATH` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/04_moge`
- `HUNYUAN_HOI_MESH_PATH` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/05_hunyuan`
- `H2M_RT_PATH` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/06_h2m`
- `ALIGNED_MANO_PATH` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/07_mano`
- `GEMINI_RESPONSES` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_29_1/compatibility/gemini_responses_category.csv`
- `OBJECT_PROMPT_CSV` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_29_1/compatibility/object_segmentation_prompts.csv`
- `FLUX_PROMPT_CSV` = `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_29_1/compatibility/flux_inpainting_prompts.csv`

## Stage inventory owners

| Stage | Files | Inventory SHA-256 | Inventory |
|---|---:|---|---|
| get_hunyuan_input | 6 | `57bbe3d889d411389f147d969e744518c06344a3e6f2ff5f357f5e2d73a2f4cf` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/01_preprocess/stage_inventory.json` |
| inpaint | 1 | `0d269ac44330319a65fdeaa0f9fb3f156e0af62fc88fb1a67549f9df891d41d2` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/02_inpaint/stage_inventory.json` |
| moge | 9 | `e11a2d6b06496f22922d2db16ecf3754e2d460c1ccdd3f5e8ef1bb01415b8c3f` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/04_moge/stage_inventory.json` |
| hunyuan | 1 | `05bbce98a8177fbf535d3f426b6deea649c38d043055b28751496a06983393ad` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/05_hunyuan/stage_inventory.json` |
| hamer | 5 | `bb8ef6cd833e245101e778dfb2ed6ffa4d11714c5c138bcb000db973605d8807` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/03_hamer/stage_inventory.json` |
| h2m | 1 | `359c46ea974a8d0acae58cd2de574cb8d9543133417015cf382c04c004ad03fe` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/06_h2m/stage_inventory.json` |
| mano_registration | 1 | `9f028cb62efafb9916c708c6488c45d3539923b7b5d5bd380e39853ae988eeaa` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/07_mano/stage_inventory.json` |

## Representative fresh assets

| Stage | Bytes | SHA-256 | Asset |
|---|---:|---|---|
| get_hunyuan_input | 13085 | `01399cf4fbec12e65a12017f7d9ab9e2a5b89785a42115d62a98a77750bec0a4` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/01_preprocess/occ/alapuse02v3n60_occ_obj.png` |
| get_hunyuan_input | 174663 | `37c98a22bc9b58d582a00e7954afe483c2814111212dae754de52745da6c967d` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/01_preprocess/cropped/alapuse02v3n60_cropped_hoi_0.png` |
| get_hunyuan_input | 22644 | `330fb19873ee3e53b8de6d7b5320c1894ec256db00b9ec8fe731e02ef4817414` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/01_preprocess/cropped_without_background/alapuse02v3n60_cropped_hoi_wo_bckg_0.png` |
| get_hunyuan_input | 778 | `b4c35ef9902f25b2414048985fb9d32c6087424aa643969102a98cbc92f67a5b` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/01_preprocess/masks/alapuse02v3n60_cropped_hand_mask.png` |
| get_hunyuan_input | 826 | `c69a5ea555320e65ece9d2dc8e65878ed0ab5c05584eb147ea6bc5f4f72d2200` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/01_preprocess/masks/alapuse02v3n60_cropped_obj_mask.png` |
| get_hunyuan_input | 188674 | `05c3dd582f0e499598c7eb6cf1088dca55af90672f8107d56530eb85c6887b20` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/01_preprocess/original/alapuse02v3n60_full_image_0.png` |
| inpaint | 892265 | `b96d6466fdca0b98c1a3a4bedc3f17d8895d03ced864f85f9ee9d67c7a7850d2` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/02_inpaint/alapuse02v3n60_inpainted_object.png` |
| moge | 51725 | `954794e8b77ca4d9466d2b952353cbf3a79fbd3ba8b27f4565b067263f3c8b65` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/04_moge/alapuse02v3n60_cropped_hoi/depth.exr` |
| moge | 6480 | `c535cd3ddd29f96212dd078874160241fd5c763347a359369cdac8716024c316` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/04_moge/alapuse02v3n60_cropped_hoi/depth_vis.png` |
| hunyuan | 2850100 | `07cedeb2576bc20382cd19870a3aed6a0b56f4b9f6ffc7bdfc77236409b8c4c2` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/05_hunyuan/alapuse02v3n60_hoi_mesh.ply` |
| hamer | 101954 | `fb79acdd516fb3ec6936c77ec4aa8862e8f95551ed723e2ef55d13e9bd83a224` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/03_hamer/alapuse02v3n60.png` |
| hamer | 52860 | `20e4d4f791047195aef2803ae482934ef723b6848e0c4aac7113e988126287fe` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/03_hamer/alapuse02v3n60_all.jpg` |
| h2m | 256 | `f657a7811648f86f5e1db2f54b6af58c87b14538f1fd2f60ded1d6774df9ffbd` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/06_h2m/alapuse02v3n60_hoi_mesh.npy` |
| mano_registration | 32921 | `ee6c723627c5cacd7c9733091b2bf0589427248aab3c6581de37e4b4c2ee5a2a` | `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_37/fresh_foundation_primary/07_mano/alapuse02v3n60_hamer_aligned_mano.ply` |

## Integration incidents closed

- Missing output-directory lifecycle: fixed at commit `b08c2dd9864805ee0e97814e1fbc7c7c0a09c218`.
- MoGe full-path `hoi` truncation: audited in `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_replay_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_38/reports/moge_full_path_hoi_truncation_incident.json` and fixed in source commit `28821d9c3346758cfc961ab3a4e4fb72fdbd001f`.
- Misplaced historical MoGe outputs remain diagnostic-only and were neither adopted nor deleted.

## Next boundary

- Build the inventory-owned Q1 evidence panel.
- Query Q1 once under its accepted policy.
- If Q1 rejects one named owner, run only that owner-specific recovery once.
- Continue through Gate-A, CPU hand registration, frame-I, Gate-C, D0, H0, H1, O0, J0, and deterministic F0.
- Foundation inventories are provenance assets, not final alignment evaluation metrics.
