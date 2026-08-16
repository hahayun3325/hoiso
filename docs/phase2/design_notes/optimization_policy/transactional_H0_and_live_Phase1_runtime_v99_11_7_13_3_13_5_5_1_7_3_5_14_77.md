# Transactional H0 controller and live Phase-1 runtime

This version repairs the pre-update gate, missing nonzero-gradient proof and incomplete rollback behavior of the earlier thin controller. It adds separate capture-only and backward-only modes. The generic runtime implements the corrected ten-method protocol over references and callbacks supplied by one synchronous production Phase-1 handoff.

The external CLI factory deliberately cannot manufacture private Phase-1 locals. Production integration must call `create_from_live_context(...)` and `run_live(...)` at the proven Phase-1 boundary. The ordinary production path remains unchanged when the opt-in callback is absent.

This source alone does not authorize H0. A real callback, default-path test, backward-only GPU preflight, zero replay and immutable unlock receipt are still required.
