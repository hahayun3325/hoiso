# Automatic reconstruction pipeline: status and completion plan

Status date: 2026-09-09. Development case: `alapuse02v3n60`.

The first scoped automatic pipeline is demonstrated. A complete, corrected command from the original input crop through reconstruction review is still under development. An accepted final reconstruction has not been established. These are three separate milestones.

## What works

- **0CP:** accepted foundation and hand inputs feed fresh Gate A, Frame I, Gate C and D0 operations, followed by retained checkpoint review. Completed-case reuse launches no new work. This starts from prepared inputs and retains downstream review evidence.
- **0CV:** the original-crop primary entry executed Q0, all seven foundation stages and Q1. After a selected-hand/frame evidence correction, replacement Q1 requested recovery. One complete seven-stage recovery executed, followed by terminal Q2. Individual completed transactions demonstrate zero-call reuse.
- Source and frame investigations recovered the intended native-hand route, verified saved joint order, corrected an ICP score/transform bookkeeping defect in an isolated copy, and staged fuller stage evidence and camera measurements.

The seven foundation stages are preprocessing, inpainting, scene geometry, object reconstruction, hand reconstruction, object-to-scene alignment and hand registration. A recovery diagnosis names the problem stage; the recovery rebuilds the complete group once. Q2 is terminal.

## What the latest audit established

The saved-tail audit, **0CV v11qa2**, passed 31 checks. All 13 outer payload hashes and eight nested failed-attempt payload hashes verify; 1,063 protected paths remained unchanged. The correction explicitly loads the pinned measurement helper before its consumers. Finite scored pixels are selected before depth subtraction. Saved pair/triple measurements reproduce exactly. There was no new fit, raster, model, producer or API/jury call.

This closes a prepared helper-loading defect and a warning-producing arithmetic expression. Neither correction improves geometry.

The latest object proposal, v11q, remains unpromoted. On 32,662 shared image pixels, overlap improves from 0.823076 to 0.853782, mean depth error falls 6.97%, and depth MSE falls 0.75%; the 95th-percentile absolute depth error rises 6.34%. Five original fixed-support pixels are lost. All 2,048 fit anchors retain visible support.

The constraint controls the average of the worst 103 predicted squared anchor errors. That quantity is not p95. On those same anchors, predicted p95 already rises from 0.09277 to 0.10059; fresh p95 is 0.09882. Thus the remaining p95 regression cannot be attributed solely to the larger evaluation set or fresh visibility. The fresh worst-103 squared-error mean also exceeds its baseline slightly, by about 0.14%. A useful approximation is still not an acceptance guarantee.

Review archive: `step_0cv_saved_tail_measurement_correction_v11qa2_review.zip`.
SHA256: `9c361e610b3ccc27c5df30dc2f593f2891322211a345c2eaa6815c050508ee79`.

## Why the complete pipeline is still missing

There are two distinct gaps: **integration** and **reconstruction quality**.

The working 0CP command starts after foundation and hand preparation. The newer crop entry, complete recovery, corrected solver guards, camera evaluator and evidence builders have been developed across separate owners. Actual historical commands still selected a legacy hand route; tested alternatives have not been enforced throughout primary, recovery and resume entry paths. Several successful checks prove isolated components or preserved receipts, not a connected live entry.

Quality also remains unresolved. Both native-hand placement candidates failed unchanged controls. Camera-guided object proposals improve some image/depth measurements while worsening others. A low ICP cost or a four-summary-metric comparison does not validate hand placement, depth tails, support coverage or physical contact. Masks and monocular depth are observations, not ground truth.

Finally, changed geometry needs fresh downstream coordinate, semantic and contact bindings. The original case's retained maps and accepted inputs cannot simply be attached to a different result. J0 acceptance remains a separate quality goal.

The recent sequence spent substantial effort isolating measurement and provenance problems. Two prepared import guards/loaders also required correction. That work makes evidence more trustworthy, but it should not be counted as completion of the missing controller. The next engineering emphasis is consolidation and integration; another unmotivated local fit would not close that gap.

## Next work and the condition for a fresh run

1. Assemble a pinned source bundle for one versioned entry implementation, recording which components are corrected, which are reference-only, and which connections remain unwritten. This is preparation, not an executable full pipeline or a complete dependency bundle.
2. Connect mandatory native-hand solver/policy settings before wrapper loading, exact-score object initialization as proposal-only, current camera evidence, and visible per-stage frame bindings. Preserve old pinned files; eliminate silent legacy fallback in the new route. Keep placement controls unchanged and propagate failed quality honestly.
3. Make one controller own Q0, the seven primary stages, Q1, at most one complete-group recovery, terminal Q2, and a bound terminal outcome. Test actual primary/recovery/resume dispatch construction. Missing bindings and ambiguous partial claims must stop before external work.
4. Connect the eligible outcome to fresh downstream configurations derived from the immediately preceding completion. Terminal rejection must produce a complete diagnostic report with no downstream geometry acceptance. A valid rejected execution is not an accepted reconstruction.
5. Run one new corrected owner on the original crop and verify zero-call completed reuse. Only then assess original-case completion and second-case readiness; `blapuse02v4n344` still needs verified input bytes and its own bindings.

**Do not rerun the unchanged old entry now.** Its full recovery already happened, and Q2 returned terminal `REJECT_CASE`. A new development run must use the corrected implementation and a new owner; it cannot reopen that transaction. There is no verified fresh-run one-line command to publish yet.

For planning, budget roughly **3–5 integration/run-review cycles after the source bundle is verified**, assuming the existing interfaces can be connected without another numerical-method change. This is an engineering estimate for testing a unified command with an honest terminal outcome, not a completion promise. No reliable cycle count or date is available for an accepted reconstruction: hand/object quality and downstream acceptance can still fail.

## Preservation and publication scope

Keep Q2 rejection, previous candidates, accepted State, 0CP receipts, runtime dependencies and historical source paths unchanged. Cleanup and second-case execution remain deferred. This note neither enables a solver nor installs an entry, changes a policy, promotes geometry or authorizes another jury request. Its publication is a documentation action.

The existing [hand solver selection note](hand_solver_selection_and_entry_requirements.md) records the intended route and retention requirements. This dated report describes the later integration and quality boundary; private evidence retains exact runtime locations.
