# TraceHOI local checkpoint integration — 2026-10-16

Development has resumed after the progress checkpoint and case handoff were published.
The base for this change is `697f41ce83817cfcd2144c945899b1933af9bb0c` on
`phase-2.1-agile-vlm-upstream-gate`. Earlier pause and resumption notes remain historical records.

## Verified progress

Q9n6Ew3N completed native imports and CPU construction of the model, VAE and
conditioner. It strictly loaded all 1,645 float16 checkpoint tensors, checked their
shapes, finiteness and exact loaded values, and verified the unchanged checkpoint
before and after loading. The worker took 33.21 seconds and exited successfully;
its service and processes were cleaned up. The returned files, manifest, prepared
components and detailed result were independently checked locally. The evidence
summary is `docs/evidence/TraceHOI_CPU_load_Q9_2026-10-16.json`.

This proves CPU component loading for the recorded environment and inputs. It does
not prove pipeline assembly, GPU transfer, inference, a generated mesh, downstream
alignment, or full parent acceptance. No new model execution is part of this publication.

## Pipeline change

`foho.geometry.hunyuan` accepts paired `--config_path` and `--checkpoint_path`
arguments, plus `--device`. The same settings can be supplied using
`FOHO_HUNYUAN_CONFIG`, `FOHO_HUNYUAN_CHECKPOINT` and `FOHO_HUNYUAN_DEVICE`;
the pipeline entrypoint forwards these values to its module processes. Explicit CLI
arguments take precedence. Omitting local paths keeps the existing pretrained loader.

Local mode uses only the specified safetensors file and YAML configuration. It does
not call the Hub loader or fall back to downloading. Cache symlinks and extensionless
content-addressed blobs are accepted. The six configuration targets are fixed to the
reviewed Hunyuan classes. All three groups are required and loaded strictly on CPU,
converted to float16, set to evaluation mode, and checked against checkpoint values.
The load/convert/release order follows Q9 to avoid retaining all original checkpoint
tensors alongside all float32 component copies. The scheduler and image processor
are then constructed, the pipeline is assembled on CPU, and an explicitly requested
device transfer follows. The installed pipeline's `to()` returns None, so the wrapper
retains the pipeline object. The local loader is not a sandbox or a service resource limiter.

Existing case ownership, one-image/one-mesh behavior, output filenames and partial
export handling remain covered. Local files are user-selected; the runtime loader
does not replace Q9's full file hashes or service lifecycle checks.

## Validation and next runtime milestone

The native-free regression suite covers strict-load failures, tensor/device/value
mismatches, configuration rejection, local path handling, CPU-first assembly,
environment and CLI routing, and the existing geometry handoff. It uses lightweight
substitutes, not installed torch or Hunyuan. The publication script runs it before
and after applying the exact patch, then commits and pushes normally.

Next runtime work is a bounded assembly check using these repository loader sources,
followed by a single named case with recorded inputs, GPU budget and output checks.
That run must establish mesh validity and the MoGe-to-Hunyuan-to-H2M handoff before
batch execution. Keep failures and denominators alongside successes. No accuracy,
real-time, geometric-bound or full-pipeline claims follow from the CPU load result.

## Cleanup

After remote publication is verified, the script archives and trashes only the two
superseded CPU attempt folders N7l4Cu9L and P8m5Dv2M. Original terminal guards,
current Q9 evidence, repository notes, models and inputs stay in place. See
`TraceHOI_retention_2026-10-16.md`. A changed or unexpected file prevents that folder's
cleanup and is reported in the return ZIP. No wildcard deletion is used.
