# H0 inline loss closure and callback contract

The reusable H0 controller is CPU-closed. Production Phase 1 currently keeps rendering, loss assembly, backward, optimizer step and state writes inline. The integration must expose those operations as closures while preserving the live autograd graph.

The callback is default-disabled. A handled callback owns the complete H0 update transaction, so the legacy hand loop is skipped; otherwise the old path remains unchanged. This prevents double optimizer steps. Frozen values are monitored through the phase-scoped frozen-state hook; only global hand rotation and translation are trainable.

Before GPU use, tests must prove exact live tensor identity, finite nonzero selected gradients, absent frozen gradients, default-path equivalence, post-update metric recomputation, rollback and zero-update integrity.
