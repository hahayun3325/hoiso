# TRACE-HOI progress checkpoint and resumption — 2026-10-15

Status: **Resume module integration after publishing this checkpoint and completing duplicate cleanup.** The developer explicitly reversed the earlier pause decision on October 15. [The earlier pause note](TraceHOI_development_on_hold_2026-10-15.md) remains a historical record. Its ON HOLD status is superseded by this note; its measured outcomes and unresolved failures remain valid.

## What is established

Scoped initialization, preprocessing and the MoGe worker/parent-decoding handoff have been verified in their recorded attempts. Hunyuan's process control, identity, evidence and completion handling passed source/fixture reviews and model-free service rehearsals. M6k3Bt8K passed sixteen native imports, fourteen supporting source checks, an observed zero exit and cleanup. Those results do not establish Hunyuan construction, weight loading, inference, mesh acceptance or complete pipeline acceptance.

The latest CPU-loading attempts both stopped before submission:

| Attempt | Observed result | Consequence |
| --- | --- | --- |
| N7l4Cu9L | Recorded 26.841 GiB available, below its 28 GiB admission threshold; 17 read-only manager calls; no worker. | Actual CPU construction and loading were not tested. |
| P8m5Dv2M | `pinned_busctl_changed`; zero manager calls or workers; memory gate not reached. | Its proposed 20 GiB worker / 24 GiB host threshold and 1,645 tensor checks remain untested on real models. |

P8 expected `/usr/bin/busctl` SHA-256 `86e0c53fed90e008065effdc169262fc7b6723c68e0eede2dc64b9468930d9d4` and observed `d420390b77dfa154c9fbf413462b59ef3132b19facf994af483e8bf62f8d5908`. Both reported 92,664 bytes. The cause of the change has not been established. `cleanup_verified=false` on this pre-submission failure does not by itself indicate a leaked process. Do not erase old terminal guards, rerun used attempts, or silently replace the pin.

Hunyuan object-only inference, FLUX, HaMeR, hand-specific Frame-I and final parent/evidence acceptance remain unfinished. Full P2 readiness is false, and the recorded Q2 result remains REJECT_CASE. No claim of a successful full reconstruction follows from this checkpoint.

## Code being preserved

The server inspection identified checkout `/home/fredcui/Projects/FollowMyHold`, branch `phase-2.1-agile-vlm-upstream-gate`, HEAD `36bf6ed353ff6be984bb7235fda69437caf6f28c`, remote `hahayun3325/hoiso`, four modified tracked files and sixteen new files. The index was empty. Its only inventory limit was a deeply nested historical Phase-1 documentation folder; there were no inspection errors. The remote had not yet been refreshed.

This commit preserves the existing Frame-I/Gate-C adapters, selected-hand registration and solver, explicit post-Q2 dispatch boundaries, optional hand solver/policy bindings, H0 hook, associated tests/configuration, and the small `tools/hoiso_auto` utilities. These are work in progress, preserved without changing their behavior. The API utility reads its credential from the environment; running it is not part of this publication.

A source snapshot of P8's Hunyuan diagnostic components and local fixture tests is retained under `tools/tracehoi/checkpoints/hunyuan_cpu_budget_P8m5Dv2M/`. This is historical diagnostic code with original pins and used attempt identities. It is not a runnable resume entrypoint or a promoted production adapter. Original reports, checkpoints, caches and large nested evidence archives stay outside Git; the snapshot manifest records source provenance and retained evidence checksums.

Publication validates Python/JSON syntax and exact staged/committed contents. It does not claim new functional tests of the server's model pipeline. The commit ID and successful remote readback belong in the external publication receipt, because a commit cannot contain its own final identity.

## Integration sequence after publication

| Boundary | Required connection and evidence | Current status |
| --- | --- | --- |
| Input → preprocessing → MoGe | Preserve case/image identities, coordinate conventions, output bindings and parent decoding. | Scoped paths verified; preserve their acceptance scope. |
| Object construction/loading | Explain the changed tool identity, check current resources, then use a fresh attempt to construct on CPU and strictly load the pinned checkpoint. | Blocked before actual loading in N7/P8. |
| Object inference → accepted mesh | Connect the tested loader to bounded inference and mesh decoding; validate finite geometry, scale/frame conventions, ownership and failure output. | Pending. |
| Hand/image modules → Frame-I | Connect real FLUX/HaMeR outputs and selected-hand registration through explicit contracts. Check handedness, camera/crop transforms, scale and input lineage. | Implementation exists in part; full acceptance pending. |
| Gate-A/Frame-I/Gate-C → refinement | Dispatch only explicitly supported real stages. Keep mock receipts and rejected evidence from advancing accepted state. | Adapters preserved; generic later-stage execution is not complete. |
| Parent orchestration → final output | Join actual worker results, cleanup, receipts and acceptance into one reproducible path; verify cached reuse without fresh model calls. | Full parent acceptance and zero-call reuse pending. |

The next integration change should be driven by the returned current automation sources and tool/package metadata. Start with the actual object-loader boundary and a small explicit adapter contract, rather than treating another source-review return as model progress. Preserve a case-level trace recording inputs, stage outcome, outputs, budgets and failure reason. Later stage acceptance must remain false until its required outputs and evidence exist.

## Research context

The WACV 2027 Round 2 submission was rejected. The private analysis `TraceHOI_WACV2027_reviews_and_next_steps_2026-10-15.md` highlights inference clarity, narrow comparisons, diagnosis independence, coverage/selection bias, uncertainty, generality and resource reporting. The engineering continuation should make the actual computation and failure ownership easier to follow. Any later scientific claim needs matched-budget/resolution comparisons, an equal-budget blind-rerun control, independent diagnosis assessment, all attempted-case denominators and paired uncertainty. Those experiments have not been completed by this checkpoint.

Reviewer identities, individual scores, private comments and review images stay in the private research record. The separately proposed MDF12 visibility-gap study is outside this continuation package.

## Preservation and cleanup

Publish on the inspected branch using a normal push after checking the refreshed remote is an ancestor of the inspected local HEAD. Stop on source drift, staged changes, unexpected Git operations or remote divergence. Preserve any partial commit/output and return its receipt; do not reset or force push.

Trash only exact, verified duplicate Downloads copies of the M6, N7, P8 and pause-inspection ZIP/terminal pairs, after remote publication is verified. Keep the original attempt directories, home terminal guards and all unique historical documents/evidence. The earlier pause note remains useful history and is retained with a supersession banner. The incomplete deep documentation inventory is not a basis for bulk cleanup.

This note records the intended handoff. Successful publication and actual cleanup must be established from the returned receipt, not inferred from this document's existence.
