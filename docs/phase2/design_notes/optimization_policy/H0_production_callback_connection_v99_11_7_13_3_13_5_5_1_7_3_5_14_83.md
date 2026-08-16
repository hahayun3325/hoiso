# H0 production callback connection

The production Phase-1 loop owns the live hand tensors and differentiable rendering path. The callback connection exposes those live references and a loss-recomputation closure without copying or detaching them. H0 may then own the global rotation/translation transaction, while scale, MANO geometry, object state, camera and targets remain frozen.

The connection is opt-in. With `h0_live_callback=None`, the original hand loop remains structurally identical. A callback must return a dictionary containing a literal Boolean `handled`. `handled=True` suppresses exactly the legacy hand loop, preventing a double optimizer step; `handled=False` executes the original loop once. Callback exceptions propagate and cannot silently fall through to a legacy update.

This patch does not itself authorize GPU execution. A real synchronous callback binding, backward-only GPU preflight, zero-update replay and immutable unlock receipt remain required.
