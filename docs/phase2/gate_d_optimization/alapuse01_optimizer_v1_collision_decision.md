# alapuse01 — optimizer-v1 collision decision

## Decision

```text
optimizer-v1 exploratory contact-only: PASS_WITH_LOCAL_COLLISION_WARNING
````

## Evidence

The contact-only optimizer improves local contact distance:

```text
full_object mean distance: 0.07499 → 0.07114
p5 distance:               0.01180 → 0.01101
within 3 cm ratio:          0.1979 → 0.2147
within 5 cm ratio:          0.3792 → 0.4190
```

But it introduces local collision risk:

```text
new very-close vertices under 5 mm: 5
ratio: 0.00643
minimum optimized distance: 0.00136
```

Visual inspection shows the red risk markers are around the intended finger/laptop contact area, not spread across unrelated hand regions.

## Interpretation

This is not a failure. It means verified contact is useful, but contact attraction alone is incomplete.

## Next step

Implement optimizer-v2 with collision repulsion.

Important: optimizer-v2 collision relief will reduce penetration, but it will not fix the laptop's global scale/location. Laptop alignment requires a separate object pose/scale/articulation repair step.
