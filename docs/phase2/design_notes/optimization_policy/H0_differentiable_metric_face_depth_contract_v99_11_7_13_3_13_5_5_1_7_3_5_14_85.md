# H0 differentiable metric face-depth contract

This helper interpolates caller-supplied camera-space vertex depth over the
nearest visible triangle using rasterizer face IDs and barycentric coordinates.
It does not choose a camera convention, invert depth, normalize per image,
detach tensors, or move data to CPU. The production adapter must supply vertex
depth in the exact signed metric camera used by the accepted Gate-A raster.

For H0 the object raster is frozen and cacheable; the hand fragments and metric
depth are recomputed from live hand R/t. O0 and J0 must rerasterize every moving
object state. This helper is not production-authorized until camera ownership,
default-equivalence, no-double-step, rollback, and real backward-only tests pass.
