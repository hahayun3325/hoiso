# TraceHOI native handoff — 2026-10-18

The T4 return published the visual-to-centered optimizer bridge at
`5a12716f807c5713d77f512e5ca7573766ec0567`. Its current native source census
showed that the caller still loads a hand in Hunyuan coordinates, applies the
object Hunyuan-to-MoGe transform to it, and runs legacy initialization phases.
Those operations would replace or incorrectly transform the saved visual pose.

The opt-in native handoff consumes the original HaMeR mesh and the T4 centered
scale, quaternion and translation together. It bypasses the old hand-frame
conversion and skips hand-only and object-only initialization. The current
phase-2 helper clones incoming parameters without resetting their values. The
existing joint rectified-flow guidance remains downstream of initialization.
No contact or collision objective selects the CPU initial pose.

`src/foho/geometry/native_handoff.py` provides a source-bound private adapter.
It verifies the two captured native source hashes and the bridge receipt,
compiles only a private copy of the native call, and leaves the installed class,
module globals and third-party files unchanged. A preview of the patched source
is included as text. Native mesh vertices and topology are checked again when
the tensor backend consumes the state. Conflicting legacy callbacks, hand paths
and FOHO environment hooks are refused. The original API remains unchanged.

The CPU checks execute the changed seam and current phase-2 helper ASTs with
test doubles. They verify exactly one hand transform, preserved initial values,
the two skipped branches, seven optimizer parameter groups and the untouched
default path. This is not native tensor, renderer or model validation.

## Runtime boundary

The reusable `bind_pipeline` API returns a callable adapter without running the
pipeline. A later caller must supply the fresh-scene camera/renderer, exact
masks, object transform, HaMeR guidance data and compatible model configuration.
Its invocation enters the native rectified-flow loop; this step does not invoke
it. `backend_execution_ready`, `native_execution_verified` and
`rectified_flow_executed` remain false. The next step is to validate those runtime
inputs, followed by a bounded native preflight. Object completeness must remain
an explicit check when later optimization changes object geometry.

Human visual review remains complete. Independent mask reference, metric scale,
physical contact and final placement are still unverified. These do not prevent
constructing a provisional visual initializer; they remain separate evidence.

## Evidence and retention

The manual server carrier authenticates the complete T4 return and original
terminal, compares the live native source bytes, runs code and real-packet checks
before and after installing five additions, and pushes normally from the T4
commit. After successful publication and replacement evidence, only the exact
T4 working tree is archived and moved to Trash. Unknown files stop retirement.
Keep original terminal guards, complete evidence archives, source inputs,
model checkpoints, human review JSON and all current partial outputs. Never
empty Trash or remove terminal guards to rerun an old attempt.
