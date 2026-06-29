# alapuse01 — next step after optimizer-v1

## Current status

Optimizer-v1 proves that the verified right-index/contact target is useful, but it also creates local collision risk.

## Immediate next step

Implement:

```text
optimizer-v2 = contact attraction + collision repulsion
````

Purpose:

```text
keep the improved index/laptop contact while pushing away unsafe very-close vertices
```

## Important limitation

Optimizer-v2 collision relief will not fix the global laptop alignment issue.

The laptop is still too small / shifted relative to GT because the current optimizer does not optimize object scale, object 6-DoF pose, or hinge state.

## Required future object-alignment step

Add an object-repair mini-gate before final Gate D:

```text
Gate D-0: object scale + 6-DoF pose + hinge-angle repair
```

Variables:

```text
object global scale
object root rotation / translation
screen part pose or hinge angle
keyboard/base root pose
small hand global correction only
```

Suggested order:

```text
1. object scale repair
2. object root pose repair
3. hinge / part pose repair
4. verified contact attraction
5. collision repulsion
```

## Claim boundary

Current optimizer-v1/v2 can support a contact-pipeline claim, not a GT object-alignment claim.

A GT object-alignment claim requires object pose/scale/articulation optimization.
