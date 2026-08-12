# alapuse02v3n60: fixed-object transform ownership and MoGe scale recovery

## Incident

The part-aware Gate-A laptop replaced the native Hunyuan object, but the fast-track continued to apply an H2M similarity calibrated for the native Hunyuan source. The matrix was numerically valid but semantically owned by a different source mesh. This produced a severely misscaled object before the first optimizer update.

## Evidence

- The native Hunyuan mesh and fixed Gate-A laptop have different SHA-256 identities.
- Applying the old H2M to the fixed laptop reproduces the rejected live step-zero object.
- The fixed-to-MoGe v3 matrix is owned by the fixed Gate-A source.
- The v4 shared-transform artifact preserves the whole/lid/base topology and part relationships.
- Exact masked MoGe support evaluation strongly prefers the v4 candidate:
  - support-to-object median distance decreases by 95.35%;
  - support-to-object RMSE decreases by 62.07%;
  - object-to-support median decreases by 24.74%;
  - object/support diagonal ratio improves from 1.6278 to 1.1585;
  - 79.50% of support lies within 0.02 and 86.33% within 0.05;
  - frozen-hand-to-candidate median distance is 0.01369.

Some complete-mesh-to-visible-support tail and centroid diagnostics worsen. This is expected to remain a review signal because the point map contains only the visible single-view surface while the fixed mesh contains complete and occluded geometry.

## Correct contract

fixed Gate-A source -> manifest-owned fixed_to_MoGe exactly once -> canonical MoGe object -> identity residual object transform -> object-only refinement -> joint-flow refinement -> Gate-D

The fixed branch must bypass the native H2M. The native Hunyuan branch must remain unchanged. Renderer, losses, zero-step capture, checkpoint, joint resume, and Gate-D must consume the same canonical MoGe object.

## Acceptance requirements

1. Exact source and matrix hashes reproduce.
2. Matrix direction is fixed source to MoGe.
3. The base conversion is applied exactly once.
4. Vertex order, faces, and lid/base relationships are preserved.
5. Common-coordinate visual placement is plausible.
6. Gross hand/object penetration is absent.
7. A corrected zero-update capture reproduces the candidate.
8. One fresh 0/5/0 run does not worsen support, contact, topology, or visual scale.

## Operational lesson

A transformation is inseparable from its source coordinate system. Passing matrix algebra, finite values, and an exact replay do not establish semantic correctness when the source mesh has been replaced. Every future fixed-object case must carry source hash, transform direction, destination frame, topology hash, and exactly-once application evidence.

## Next route

Close visual and penetration review, inventory and write the opt-in source seam, CPU-replay the new canonical object, capture corrected step zero, run one bounded 0/5/0 object-only stage, and only then proceed to joint flow and Gate-D.
