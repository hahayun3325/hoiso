# alapuse02_v3 shared-frame dry-run v1 decision

## Files

- visual: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02_v3/integrated_gates/shared_frame_dryrun_v1/visuals/alapuse02_v3_shared_frame_dryrun_v1.glb`
- report: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02_v3/integrated_gates/shared_frame_dryrun_v1/metrics/alapuse02_v3_shared_frame_dryrun_v1_report.json`
- hand: `/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse02_v3_selector_v41_refined_pipeline/guidance_out/alapuse02v3_hand.ply`
- object: `/home/fredcui/foho_phase0/phase1_diagnostics/selector_v41_full_pipeline/runs/arctic_alapuse02_v3_selector_v41_refined_pipeline/guidance_out/alapuse02v3_obj.ply`

## Decision rule

If the green hand is near or touching the white laptop object:

`PASS_SHARED_FRAME`

If the green hand floats far from the laptop or appears in a different coordinate family:

`FAIL_FRAME_MISMATCH`

If the object is not recognizably a laptop or is too collapsed/fused for part splitting:

`FAIL_OBJECT_UNUSABLE`

## My decision

TODO after visual inspection.
