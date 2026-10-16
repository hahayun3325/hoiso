> Historical checkpoint: the pause decision below was superseded later on 2026-10-15. See [current progress and resumption](TraceHOI_progress_and_resumption_2026-10-15.md). Original findings and failure records remain applicable.

# TRACE-HOI development on hold — 2026-10-15

Status: **ON HOLD at the developer's request following WACV 2027 Round 2 rejection.** This is a preservation checkpoint, not a successful end-to-end run or a commitment to resume or resubmit. No new probe, model run, dependency repair, or experiment is scheduled by this note.

## Why development is paused

The submitted work was *TRACE-HOI: Bounded Failure Routing for Part- and Contact-Aware Single-Image Hand-Object Reconstruction*. The private review analysis dated October 15 records the rejection and common concerns about the clarity of the inference procedure, routing and recovery rules, limited comparisons, independent validation of diagnosis, and evaluation coverage. Those concerns are distinct from the engineering milestones below. Passing a diagnostic does not establish a research claim or validate the entire pipeline.

The reviews also recognized the practical reconstruction problem and useful coordination/refinement ideas. If the work is revisited, it needs a concrete inference description and stronger comparative evidence: matched hardware/resolution and budgets, an equal-budget blind-rerun control, independent diagnosis labels, failure/coverage denominators, paired uncertainty, and representative failures. These are future research requirements, not completed experiments. The private analysis's separate visibility-gap/MDF12 study remains a proposal and is not started by this checkpoint. Reviewer identities, individual scores, private comments, and the review screenshot are intentionally kept in the private research record.

## Engineering progress at the pause

| Area | Established scope | Remaining limit |
| --- | --- | --- |
| Earlier case preparation and preprocessing | Scoped initialization and the recorded W7u4Lc9Q preprocessing stage were completed. | This does not establish acceptance of the whole reconstruction. |
| MoGe | The B4z9Rh6X scoped MoGe worker and parent decoding, followed by the C5a2Sj7Y handoff review, were completed. | Preserve their original case/input and scope restrictions. |
| Hunyuan control and evidence machinery | Source/fixture reviews and bounded live rehearsals covered service identity, stop/release ordering, and saved completion evidence. A3y8Qg5Y completed a model-free end-to-end completion rehearsal. | These rehearsals did not execute Hunyuan inference or prove final parent acceptance. |
| Hunyuan native imports | M6k3Bt8K passed all sixteen imports, fourteen supporting source rechecks, exit-zero observation, and service cleanup. | No model construction, checkpoint loading, or inference in M6. |
| Hunyuan CPU construction and strict loading | N7 and P8 were prepared to check 1,645 state tensors, including shapes, finiteness, strict loads, and exact CPU F16 values against a pinned checkpoint. | Both stopped before worker submission. Actual construction/loading remains untested by these attempts. |
| Full pipeline | Code, scripts, fixtures, and original success/failure records are retained. | Hunyuan object-only inference/mesh acceptance, FLUX, HaMeR, hand-specific Frame-I, complete parent/control/evidence acceptance, zero-call reuse, and eligible downstream/J0 remain pending. P2/global readiness is false; Q2 remains REJECT_CASE. |

Many earlier returns are source reviews or simulated callback checks. Their count must not be interpreted as a count of completed reconstructions. The retained local verification ledger now contains 370 standalone pairs: 336 successful within their stated scopes and 34 HOLD, separately from 319 source-review and three documentation pairs. A different historical reported N7 HOLD still lacks original-file verification and is not N7l4Cu9L.

## Exact stopping point

**M6k3Bt8K — successful native-import diagnostic.** The worker used `TORCHINDUCTOR_COMPILE_THREADS=1`, with compiler helper launches blocked. Resource limits were 90 seconds, 4 GiB and 32 tasks. Native imports may query the CUDA driver; the probe performed no explicit CUDA work. Its originals passed 317 local evidence checks.

**N7l4Cu9L — HOLD at host-memory admission.** The saved result reported 28,820,393,984 bytes (26.841 GiB) available, below a 28 GiB threshold for a 24 GiB worker. Seventeen read-only manager calls occurred; no service was submitted. The original raw memory text was not saved, so this number is a recorded result rather than an independent reparse of retained text. Original files passed 144 local evidence checks.

**P8m5Dv2M — HOLD at the tool identity check.** This successor reduced the worker cap to 20 GiB and required 24 GiB host availability, retaining the N7 loader and all 1,645 tensor checks. Its local tests passed 365 checks on each of Python 3.9 and 3.12; these were fixture tests, not actual model loading. On the server it stopped with `pinned_busctl_changed`:

- Expected `/usr/bin/busctl` SHA-256: `86e0c53fed90e008065effdc169262fc7b6723c68e0eede2dc64b9468930d9d4`.
- Observed SHA-256: `d420390b77dfa154c9fbf413462b59ef3132b19facf994af483e8bf62f8d5908`.
- Both observations reported 92,664 bytes. The retained evidence does not establish why the binary changed.
- Zero manager calls; no service submission or stop; no model construction, weight loading, inference, or explicit CUDA work. Memory admission was not reached.
- `cleanup_verified=false` is an unfulfilled/default observation for this pre-submission failure, not evidence that P8 leaked a worker. This also does not certify the state of unrelated services.
- Original ZIP and terminal passed 123 local checks, including prepared components, manifest/CRC, prior evidence, source preflights, and report/terminal agreement.

Do not rerun the used M6, N7, or P8 attempts, remove their terminal guards, or silently replace the pinned tool hash. Any future continuation requires a fresh environment review and a new attempt identity.

## Retained evidence

The following originals are expected in `/home/fredcui/Downloads` and their respective original attempt folders or home terminal paths. Preserve originals even when redundant transfer copies are moved to Trash.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `alapuse02v3n60_hunyuan_native_compiler_serial_probe_20261014_v1_M6k3Bt8K.zip` | 1190485 | `143a3ecb011f0d1212080bc2abafae404bf21445d417f4ae9961161d507c1dfd` |
| `hunyuan_native_compiler_serial_probe_M6k3Bt8K.terminal.txt` | 1450 | `5df4b06aaea53ce23fe466f44916fbef2aae329f3a091ac374e0ef9bf0641c4f` |
| `alapuse02v3n60_hunyuan_cpu_load_probe_20261014_v1_N7l4Cu9L.zip` | 1277011 | `0e498b6e0469e9abf90971c3879739b15b4969077f9f85efba6dc242c9ba35b4` |
| `hunyuan_cpu_load_probe_N7l4Cu9L.terminal.txt` | 1373 | `3332042e6588a8c768317300921a6086ea37f8dbee9d21494244abede33c844e` |
| `alapuse02v3n60_hunyuan_cpu_budget_probe_20261014_v1_P8m5Dv2M.zip` | 1356498 | `2213c4c2d4a1a0a62de5f0bbd6713315a34319f5ee1c1667fbbbab580ecd09fd` |
| `hunyuan_cpu_budget_probe_P8m5Dv2M.terminal.txt` | 1530 | `c925b53c748c5882ad5e0a53ab7d87e7a1ff89caa617ed205cc60b76df82585a` |

Latest prepared server script: `hunyuan_cpu_budget_probe_P8m5Dv2M_server.sh`, SHA-256 `03c73b4b4abd437556a5e1bf5ceb1fe2078c853a1fda691a5871224b2f655fc7`. Collector: `collect_returns_P8m5Dv2M.sh`, SHA-256 `e3fb581375a7d70565ec447d3561a462d9515d6fbbd5e35cea2507ec883a8b9c`. These are historical used-attempt artifacts, not resume commands.

## Repository preservation and cleanup

The working server checkout is `/home/fredcui/Projects/FollowMyHold`. The last locally known remote is `hahayun3325/hoiso`; its current server branch, staged changes, remote state, and uncommitted files must be read from the server before publication. The older Mac checkout is not evidence of the server's current Git state.

Keep this note in `docs/TraceHOI_development_on_hold_2026-10-15.md`. Inspect and preserve the server's current source edits and useful maintained scripts, then commit an explicitly reviewed path list and push normally from the server. Preserve unrelated staged/unstaged changes. A successful local commit alone is not proof of a successful GitHub push. Record the final commit, branch, remote, and push verification in the handoff receipt.

Generated one-shot scripts may contain embedded prior ZIPs. Do not indiscriminately add all home scripts, evidence archives, checkpoints, caches, credentials, private reviews, or datasets to Git. Use the source modules and wrappers appropriate to the repository, retaining complete evidence separately with checksums. No code was promoted into the application merely because its diagnostic passed.

Cleanup must use a manifest of exact paths and retained copies. Move only verified duplicates or clearly superseded generated documents to recoverable Trash, with restore information. Keep failed evidence, final source snapshots, the submitted manuscript, private review analysis, and this pause note. No recursive deletion of the repository, attempt directories, environments, model caches, or datasets is authorized by this checkpoint.

At preparation time, the pause note and server inspection commands are ready locally; no new server commit or GitHub push has been observed. Publication and broader server cleanup await the inspected file inventory.

## If development is resumed later

1. Make an explicit decision about scope; the pause does not authorize new experiments.
2. Read this note and the original failure records. Inspect current Git changes, environment/tool identities, available memory and retained inputs before editing anything.
3. Reconcile the changed `busctl` binary from evidence rather than changing its expected hash blindly. Use a new attempt identity if a future run is approved.
4. Establish actual CPU constructor/checkpoint loading before claiming it passed; then assess the remaining inference and acceptance stages separately.
5. For any future research claim, address the comparison, independent-validation, coverage, and clarity questions above. Do not treat the existing engineering checks as substitutes for those experiments.

Source for rejection context: private local note `TraceHOI_WACV2027_reviews_and_next_steps_2026-10-15.md`, read on October 15, 2026. The manuscript/review history and its proposed follow-up study remain separate from this paused implementation record.
