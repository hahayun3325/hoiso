# H0 hook-bundle ordered-allowlist recovery

The H0 phase loader returns an ordered list of the two live trainable tensors:
global hand rotation followed by global hand translation. The first hook
packer incorrectly required a name-keyed mapping at its optimizer boundary.

The recovered packer follows the loader's real contract and still enforces the
same safety invariant: only the two exact live tensor objects, in the frozen
phase-config order, can enter the optimizer. Mappings, copies, detached
tensors, swapped order, duplicates, missing owners, and extra owners are
rejected.

This recovery is reusable infrastructure. It performs no GPU work and does
not make H0 executable. Real Phase-1 loss, metric depth, dense/r04 object,
gate, state, checkpoint, and capture closures plus one case launcher must be
bound and tested before the backward-only preflight.
