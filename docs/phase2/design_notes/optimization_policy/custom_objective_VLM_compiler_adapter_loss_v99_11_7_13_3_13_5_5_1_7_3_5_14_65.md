# Custom objective: VLM semantics to geometry-owned losses

Generated: 2026-08-16T00:46:13.526739+00:00

The VLM sees the case image and frozen Gate B/D0 prompt. It returns semantic
names and relations such as index/middle to upper lid rim. It never emits
vertex IDs, face IDs, transforms, metric depth, learning rates, or weights.

The compiler validates the response and maps semantic names to current,
hash-owned MANO pads/joints and Gate-A face regions. The adapter freezes every
live parameter, enables only the phase allowlist, and routes fixed-policy loss
terms to the selected owners. The selected contact loss measures only the
reviewed pads against the reviewed object patch; forbidden clearance,
penetration, observation, trust-region, and dense-valid z-order terms remain
active as specified by the global policy.

The dense Gate-A raster is deterministic renderer output, not MoGe. It gives
the current mesh's dense depth and visible face IDs. MoGe is learned image
geometry evidence. MoGe supervises what the image suggests, while the Gate-A
raster supplies model ownership and occlusion geometry. The raster is cached
while Gate-A is frozen and regenerated after an object update.
