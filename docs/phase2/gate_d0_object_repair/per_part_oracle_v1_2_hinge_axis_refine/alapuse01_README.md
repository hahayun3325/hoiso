# alapuse01 — Gate D-0 per-part oracle v1.2 hinge-axis refinement

## Goal

Refine the connected-hinge oracle model after v1.1.

## Why v1.2 is needed

V1.1 fixed collapse and scale, but screen/base still visually misalign with GT.

The likely causes are:

- weak hinge-axis estimate
- weak hinge-center estimate
- keyboard_base root pose fitted to whole GT object instead of base region
- noisy / fragmented Gate A part meshes
- whole-GT scoring instead of part-aware scoring

## V1.2 target

Keep:

- one shared global scale
- keyboard_base as root
- no independent per-part scale
- no independent screen translation

Improve:

- search multiple hinge axis candidates
- search small hinge-center offsets
- compare v1.1 vs v1.2 metrics
- keep collapse guard
- add stronger visual diagnostics

## Success condition

V1.2 is successful only if:

- collapse_flag remains false
- bbox volume remains close to 1
- screen/base visually align better with GT
- hinge remains connected
- symmetric metric does not become much worse

## If v1.2 passes

Run Gate C v3 contact verification in the repaired frame.

## If v1.2 fails

Inspect Gate A part quality and consider pseudo-GT part decomposition / silhouette-based repair.
