# H0 case callback factory and depth boundary

The production callback seam supplies live Phase-1 tensors. The case callback
factory converts one complete live-context dictionary into the tested
transactional H0 runtime. It is intentionally one-shot and delegates all
backward, snapshot, rollback, gate, capture, and future update behavior to the
transactional controller.

The factory does not invent geometry or depth conversions. Production must
supply the complete ten-hook dictionary. Gate-D0 index/middle and r04 owners
must be hash-bound, and dense z-order may be activated only after the renderer's
hand output is converted to metric camera depth by an explicit owner. The CPU
test proves interface behavior only; it does not authorize a GPU preflight or
an H0 update.
