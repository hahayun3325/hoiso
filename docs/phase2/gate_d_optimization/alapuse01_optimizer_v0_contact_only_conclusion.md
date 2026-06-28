# Gate D — optimizer v0 contact-only conclusion

## Setup

Optimizer v0 uses:

```text
global hand translation only
contact attraction only
alpha cap = 0.75
no object movement
no collision loss
no joint update
no overwrite of original meshes
````

## Verified contact

```text
right index → base_edge_or_hinge_region
semantic primary part: keyboard_base
support parts: keyboard_base + hinge
```

## Numeric result

```text
before patch_mean = 0.026355
after  patch_mean = 0.015449

before loss = 0.00074749
after  loss = 0.00028732

best_alpha = 0.75
best_shift_norm = 0.01239000486055104
mean_improved = True
loss_improved = True
```

## Visual result

The optimized scene looks like the selected alpha=0.75 preview.

```text
right index contact improves
no obvious penetration from visual inspection
no obvious global hand drift
```

## Decision

```text
Gate D optimizer v0 contact-only: PASS
Next step: collision / penetration precheck
```

## Safety rule

Do not run full optimization yet. The next step should check whether the contact-only translation introduces unsafe collision.
