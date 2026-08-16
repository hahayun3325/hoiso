# H0 trainable registry and frozen-state hook

H0 owns only live global hand rotation and translation leaves. Hand scale, current MANO geometry/articulation, Gate-A object state, camera, and other immutable values are not required to be optimizer leaves. They are supplied by a `frozen_state` hook and hashed before/after every transactional update.

This prevents the controller from calling `requires_grad_` on derived MANO geometry while retaining numerical immutability checks and rollback. H1 remains responsible for independently binding real MANO articulation parameters. Production is not connected or authorized by this interface change.
