# Gate D — contact-only smoke preview conclusion

## Verified contact target

```text
right index → base_edge_or_hinge_region
semantic primary part: keyboard_base
support parts: keyboard_base + hinge
````

## Numeric result

The contact-only smoke preview improves local contact distance and attraction loss.

```text
alpha 0.00: patch_mean = 0.026355, L = 0.00074749
alpha 0.50: patch_mean = 0.018967, L = 0.00040969
alpha 0.75: patch_mean = 0.015449, L = 0.00028732
alpha 1.00: patch_mean = 0.012288, L = 0.00019752
```

## Visual result

```text
alpha 0.50: improves contact and looks safe
alpha 0.75: best visual balance
alpha 1.00: too tight, possible penetration
```

## Decision

```text
Gate D contact-only smoke preview: PASS
Selected safe alpha: 0.75
Next step: Gate D optimizer v0 with contact-only, small hand global translation, and no permanent overwrite
```

## Safety rule

The optimizer v0 should use alpha 0.75 as the maximum safe target. It should not force the hand all the way to alpha 1.00.
