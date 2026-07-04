# aket01 Gate D sandbox v0.2a final decision

## Decision

SDF_UNRELIABLE_BODY_NOT_WATERTIGHT.

## Evidence

The SDF sanity script ran successfully.

Mesh quality:
- is_watertight = false
- is_winding_consistent = true
- euler_number = -14
- num_components = 2
- largest component = 11095 vertices
- stray component = 49 vertices

Probe signs:
- bbox center probe is negative, as expected for an inside point.
- six outside-axis probes are positive, as expected for outside points.

## Interpretation

The global SDF sign convention is not completely broken, but the object body mesh is open and fragmented.
Therefore, exact signed-distance penetration depth should not be used as a final physical measurement.

## Consequence

Do not use raw igl.signed_distance for v0.3 correction.
Use a robust fallback collision proxy:
- largest body component only
- nearest surface samples
- local normal push-out
- visual audit
