# Reusable H0 hook bundle and callback launch bridge

The hook packer validates an exact two-tensor H0 parameter registry and an
exact nine-owner closure set, then adds the tenth hook: an identity-checked
global-R/t optimizer builder. It contains no case-specific geometry, semantic
weights, or detached trainable copies.

The launch bridge accepts only a target with an explicit keyword-only
`h0_live_callback=None` parameter. It preserves callback identity and refuses
implicit `**kwargs` ownership or a duplicate callback argument.

These are reusable infrastructure pieces, not the live production binding.
Production must still supply D0-aware loss, metric hand depth, frozen object
raster, post-update gate, state, checkpoint, and capture closures; one exact
case launcher must still be selected and tested before GPU execution.
