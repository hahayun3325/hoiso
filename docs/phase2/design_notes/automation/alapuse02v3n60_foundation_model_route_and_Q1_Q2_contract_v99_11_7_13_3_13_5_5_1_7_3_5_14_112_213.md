# alapuse02v3n60 foundation-model route and Q1/Q2 contract

## Recorded status

- Source head: {head}
- Q1 result: {verdict}
- Next route: {route}
- Q1 audit: {audit_path}

This note separates semantic identity, reconstruction, registration, and jury
control. A closed file inventory proves provenance; Q1/Q2 proves semantic
acceptability.

## Foundation route

~~~mermaid
flowchart TD
  A[Accepted crop] --> Q0[Q0: laptop identity and selected hand box]
  Q0 --> P[Preprocessing: object mask and selected hand mask/crop]
  P --> F[FLUX: remove occlusion / clean object image]
  F --> HY[Hunyuan: image-to-3D object mesh]
  P --> M[MoGe: scene depth and 3D carrier]
  HY --> H2M[H2M: register Hunyuan mesh to MoGe]
  M --> H2M
  P --> HA[HaMeR: local articulated hand mesh]
  HA --> VP[ViTPose: independent 2D joints]
  VP --> R[Selected-hand 7-DoF registration]
  H2M --> J[Joined seven-owner evidence panel]
  R --> J
  J --> Q1[Q1 jury]
  Q1 -->|PASS| GA[Gate A]
  Q1 -->|one owner| REC[bounded recovery]
  REC --> Q2[terminal Q2]
  Q1 -->|reject| STOP[stop]
  Q2 -->|PASS| GA
  Q2 -->|reject| STOP
~~~

## Hunyuan and H2M are different

Hunyuan consumes the cleaned object image and generates the 3D triangular
object mesh. H2M does not lift 2D to 3D. It consumes the already-3D Hunyuan
mesh and the already-3D MoGe scene mesh or point cloud, runs coarse and fine
ICP, and writes the 4x4 similarity transform that places the object into the
scene. H2M may adjust scale, rotation, and translation; it does not repair
topology, articulation, or an incorrect object mask.

## Failure-containment rules

- A bad object mask stops FLUX, Hunyuan, and H2M descendants.
- A changed selected_hand_id stops HaMeR/ViTPose/registration.
- Nonfinite or implausible geometry stops Q1/Q2.
- Q1 PASS freezes the front-half hashes and opens Gate A without rerunning.
- Q1 RETRY_ONE_OWNER permits one bounded owner recovery and terminal Q2.
- A mock post-Q2 artifact never substitutes for a real stage receipt.
