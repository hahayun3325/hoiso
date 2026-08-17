# H0 production integration retrospective and reusable optimization blueprint

Generated: 2026-08-17T01:44:20.324040+00:00

## Scope and current status

Gate-D0 semantics selected index/middle contact and the r04 Gate-A lid-rim
patch. The compiler, phase configuration, generic callback, transactional
controller, case factory, frozen-owner ledger, rollback, dense Gate-A raster,
and CPU factory bind test are closed. H0 is still locked until production live
hooks, differentiable metric hand depth, backward-only preflight, and zero replay
pass.

## Architecture

`D0 response -> semantic compiler -> geometry-owned phase config -> case factory
-> live-context adapter -> transactional controller -> default-disabled
production callback -> post-update gates`.

The generic layer owns control flow, transactions, and validation. The per-case
plug owns exact tensors, contact geometry, camera/depth evidence, closures,
hashes, and outputs.

## Challenges and lessons

1. A bounded CPU initializer can remain scientifically imperfect; it is not an
   optimization acceptance state.
2. Weighted objectives can trade depth for silhouette. Hard gates and
   post-update recomputation are required.
3. Sparse object z-buffer coverage produced an invalid z-order gradient. Dense
   valid Gate-A depth and explicit validity masks are mandatory.
4. VLM semantics must be compiled into current MANO vertices/joints and Gate-A
   faces; names alone cannot drive a differentiable loss.
5. Only live tensor identity is acceptable. Detached copies cannot receive the
   intended gradient.
6. The injected controller must prevent a second legacy optimizer step.
7. Transactions must separate tensor values from trainability flags and restore
   both after rejection.
8. Source/AST scans must target the exact production owner, not historical
   copies or substring matches.
9. Direct test execution must bind the repository `src/` import root.
10. Raw runtime results and PASS/check receipts are different schemas and must
    be validated separately.

## Non-negotiable H0 invariants

- Trainable: global hand rotation and translation only.
- Frozen: scale, MANO articulation, object pose/vertices, camera, observations.
- Metric hand depth: positive finite camera-space depth before inverse or
  min/max normalization, differentiable with respect to live hand R/t.
- Gate-A raster: cached in H0 because the object is frozen.
- Recompute hand rendering/loss after every trial update and before acceptance.
- Literal `handled=True` skips the complete legacy hand optimizer block.
- Every rejected update restores values, trainability flags, and any reusable
  optimizer state.

## Validation ladder

1. Syntax/static ownership audit.
2. CPU unit and transaction tests.
3. Independent schema-specific artifact audit.
4. Default-None equivalence, no-double-step, and rollback source tests.
5. Real backward-only GPU preflight with zero updates.
6. Separate zero-update integrity replay.
7. Immutable bounded-run unlock receipt.
8. Five-update H0 diagnostic with per-step post-update review.

## Optimization-stage blueprint

| Stage | Trainable | Frozen | Raster policy | Added responsibilities |
|---|---|---|---|---|
| H0 | hand global R/t | scale, MANO pose, object, camera | cache object; rerender hand | coarse differentiable alignment |
| H1 | selected MANO articulation owners | global anchors/object unless separately authorized | cache object; rerender hand | selected-finger contact, pose prior, anatomy/self-collision |
| O0 | object pose/articulation owners | accepted hand | rerasterize object after each update | part consistency and object evidence |
| J0 | authorized hand and object owners | camera/observations and protected anchors | rerasterize both | symmetric contact/collision and drift prevention |
| D1 | none | complete accepted state | validation renders only | final semantic/contact/collision jury |

## Memory-bounded schedule

Reuse one rasterization for silhouette and metric depth where possible. Cache
only frozen owners, release transient graphs after each transaction, use short
stages with checkpoint review, and never retain multiple full differentiable
object/hand rasters unless a measured memory budget permits it.

## Immediate route

`14_85` production hook/depth patch and CPU tests -> `14_86` backward-only real
bind -> `14_87` zero replay/unlock -> `14_88` five-update H0 review. H1, O0, and
J0 require separate phase-specific owners and authorization; they must not start
automatically from an H0 result.
