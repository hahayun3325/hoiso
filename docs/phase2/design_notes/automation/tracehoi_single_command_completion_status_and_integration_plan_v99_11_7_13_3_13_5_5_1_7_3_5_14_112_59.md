# Trace-HOI single-command completion status and integration plan

## Scope and authoritative status

Case: `alapuse02v3n60`.

Repository branch: `phase-2.1-agile-vlm-upstream-gate`.

Audited command-owner commit: `dcf4969a0b190fdb79d1231a0a712fede8676417`.

The repository has a restartable automatic route from one accepted crop through
combined Q0, seven primary foundation stages, Q1, at most one recovery lineage,
and terminal Q2.  It does not yet have an installed fresh route from Q2 PASS
through Gate A, frame-I, Gate C, D0, H0, H1, O0, J0, F0, and benchmark metrics.

## Latest case evidence

Run `trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_57`
completed all seven recovery stages and one Q2 request.  Q2 accepted the
recovered laptop mask, inpainting, MoGe scene/depth, Hunyuan mesh, HaMeR output,
and H2M output.  It returned `RETRY_ONE_OWNER` for `mano_registration`, whose
multi-view render is elongated and sheet-like.  The run is therefore
`TERMINAL_REJECTED_AFTER_Q2`, not `READY_FOR_GATE_A`.

The same panel also exposes a hand-instance continuity gap: automatic
preprocessing selected the lower hand, while this case's accepted interaction
uses the upper hand at the laptop lid.  Q0's Gate-B `hand_instance` must be
transported to the detector separately from the fixed short prompt `only hand`.

## Important installed owners

- Top-level front-half runner: `src/foho/automation/case_runner.py`.
- Q0 contract/transport: `src/foho/automation/combined_q0.py` and
  `src/foho/automation/combined_q0_runner.py`.
- Foundation manifest/controller: `src/foho/automation/foundation_manifest.py`,
  `foundation_gpu_bind.py`, `foundation_process_controller.py`, and
  `foundation_run_in_conda_adapter.py`.
- Foundation preprocessing: `src/foho/preprocess/get_hunyuan_input.py` and
  `segment_hoi_sam2.py`.
- Jury evidence/transport: `src/foho/automation/q1_evidence_panel.py` and
  `q1_responses_runner.py`.
- Current rejected automatic MANO route: `src/foho/alignment/mano.py`.
- Proven bounded CPU hand-registration owner:
  `tools/gate_c_v99_11_hand_anchor/run_v3_CPU_7DoF_global_hand_alignment_v99_11_7_13_3_6.py`.
- Existing optimizer entrypoint: `src/foho/guidance/run.py`, with the versioned
  H0/H1/O0/J0 binders and `config/optimization/` manifests documented in the
  case-study notes.

## Required data contracts

Every stage result contains: schema/version, case id, stage, source hash,
input path+hash+semantic role, output path+hash+semantic role, coordinate frame,
units, variables optimized/frozen, resource usage, terminal decision, and the
exact next-stage eligibility flag.  A stage reads only the preceding accepted
receipt; it may not discover a historical file by broad glob.

The front-half hand contract has two distinct fields:

- `gate_b.hand_instance`: `upper_image_hand`, `lower_image_hand`,
  `single_hand`, or `ambiguous`.
- `hand_segmentation_prompt`: fixed short string `only hand`.

## Implementation order

1. Localize and repair the independent clean-primary controller failure.
2. Transport Q0 hand identity through the runtime/manifest/preprocessing stack.
3. Replace free-scale MANO-to-whole-object ICP with bounded, selected-hand,
   camera/depth/mask-owned frame-I registration.
4. Add deterministic hand-geometry validation before Q1/Q2.
5. Make Q1/Q2 result schemas round-aware and retain at most one recovery.
6. Obtain one new clean `READY_FOR_GATE_A` lineage.
7. Implement `post_q2_runner` adapters for Gate A and the frame-I object/hand join.
8. Compile fresh Gate-C and D0 contracts from the joined receipt and Q0.
9. Generate fresh H0/H1/O0/J0 arguments/manifests/readiness receipts from the
   previous accepted checkpoint; never reuse historical checkpoints as outputs.
10. Add deterministic F0, same-camera export, and a generic validated evaluator.
11. Expose the whole route behind `case_runner run --through final --resume`.

## Current completion estimate

The Q0-to-Q2 orchestration infrastructure exists, but this case is blocked at
hand identity/registration and the post-Q2 path is unimplemented.  A first
honest single-case automatic final/F0 result is estimated at 4--8 working days
after the hand fix.  A benchmark-grade evaluator and fixture proof add roughly
2--4 working days.

## Safety and promotion rules

- Preserve every failed or accepted lineage immutably.
- No third semantic jury call after Q2.
- Only Q1/Q2 PASS may set `eligible_for_gate_a=true`.
- Do not treat file existence as semantic acceptance.
- Do not use the manually accepted J0 output as a fresh automatic output.
- Stop on frame, hand-owner, hash, nonfinite-geometry, or unresolved-path errors.
