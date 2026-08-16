# H0 value immutability and trainability recovery

The first transactional CPU run produced a false frozen-owner alarm because one digest mixed tensor values with `requires_grad`. H0 intentionally changes trainability flags while entering its rotation/translation-only phase.

The correction uses two independent ledgers: `state_digest` checks numerical values, while `flag_snapshot` checks that the original trainability policy is restored after capture, backward-only, accepted, rejected, and exceptional paths. A real object or frozen-parameter value mutation still triggers rollback.

This correction does not connect production or authorize H0. The remaining work is a synchronous opt-in callback that passes exact live Phase-1 tensor references and production loss/render/checkpoint hooks to the adapter.
