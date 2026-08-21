# alapuse02v3n60 foundation-model I/O route and Q0/Q1/Q2 contract

## Recorded status

- Source head before installation: `c41a68bdcd45a5b755a2a819815bbb7ab840c2fe`
- Historical source run: `/home/fredcui/foho_phase0/phase2_gateA_part_recon/cases/alapuse02v3n60_auto_v2/trace_hoi_automatic_case_v99_11_7_13_3_13_5_5_1_7_3_5_14_112_211`
- Historical Q1 transport verdict: `RETRY_ONE_OWNER(get_hunyuan_input)`
- Historical semantic accounting: `INVALIDATED_BY_PIPELINE_CONTRACT`
- Q2 calls in the run-211 lineage: `0`

Run 211 remains immutable diagnostic evidence. Its jury call evaluated a known
pipeline-contract mismatch, so it is not renamed Q2 and does not spend this
lineage's recovery round. The corrected manifest must start a fresh primary Q1.

## Foundation route

~~~mermaid
flowchart TD
  RGB[Accepted cropped RGB] --> Q0[Q0 semantic router]
  Q0 -->|laptop category and object prompt| PRE[Preprocessing and SAM2]
  Q0 -->|one selected-hand detector box| PRE

  PRE -->|object-only carrier: masked_obj_path / occ_obj| HY[Hunyuan]
  PRE -->|joint carrier: cropped_hoi_wo_bckg_path| MG[MoGe]
  PRE -->|crop plus remove-hand prompt| FX[FLUX inpainting]
  PRE -->|selected crop, box, mask, owner| HA[HaMeR]
  PRE -->|same selected owner| VP[ViTPose]

  HY -->|object-only laptop mesh| H2M[H2M]
  MG -->|depth, intrinsics, scene points| H2M
  H2M -->|object-to-scene similarity transform| JOIN[Evidence join]

  HA -->|local articulated hand mesh| REG[Selected-hand registration]
  VP -->|selected-hand 2D joints| REG
  MG -->|observation-space support| REG
  REG -->|registered MANO plus geometry receipt| JOIN
  FX -->|clean appearance reference| JOIN

  JOIN --> Q1[valid primary Q1]
  Q1 -->|PASS| GA[Gate A]
  Q1 -->|one genuine owner failure| REC[one bounded recovery]
  REC --> Q2[terminal Q2]
  Q2 -->|PASS| GA
  Q1 -->|REJECT| STOP[stop]
  Q2 -->|REJECT| STOP

  GA --> FI[frame I]
  FI --> GC[Gate C]
  GC --> D0[D0]
  D0 --> H0[H0]
  H0 --> H1[H1]
  H1 --> O0[O0]
  O0 --> J0[J0]
  J0 --> F0[F0]
  F0 --> MET[export and metrics]
~~~

## Exact semantic inputs and outputs

| Producer | Input contract | Output contract | Consumers |
|---|---|---|---|
| Q0 | accepted RGB, strict schema, case policy | laptop label/prompts and one selected-hand box/policy | preprocessing and prompt adapters |
| preprocessing + SAM2 | RGB, Q0 laptop label, Q0-selected box | laptop mask, selected-hand mask/ID, joint carrier, object-only carrier | all foundation branches |
| FLUX | cropped HOI and object-specific remove-hand prompt | clean/inpainted object appearance | evidence panel and appearance guidance |
| Hunyuan object-only carrier | `masked_obj_path` / `occ_obj` | object-only articulated laptop mesh | H2M and Gate A |
| MoGe joint scene/depth | `cropped_hoi_wo_bckg_path` | depth, intrinsics, normals, joint scene points/mesh | H2M, registration, frame I |
| H2M | Hunyuan 3D mesh and MoGe 3D scene | similarity transform placing the object in the scene | frame I and evidence panel |
| HaMeR | selected crop, detector box, SAM2 mask, selected owner | local articulated hand mesh and camera/render evidence | registration |
| ViTPose | the same selected crop/owner | selected-hand 2D joint targets | registration |
| selected-hand registration | HaMeR mesh, ViTPose joints, MoGe/H2M support, bounded policy | registered MANO mesh plus numerical/visual receipts | Q1/Q2 and frame I |
| Q1 | hash-owned seven-stage evidence panel and policy | PASS, one-owner RETRY, or REJECT | Gate A, recovery, or stop |
| terminal Q2 | recovery-only hashes after one valid Q1 retry | PASS or REJECT; no third call | Gate A or stop |

## Failure containment

- An object-mask or object-carrier change invalidates FLUX/Hunyuan/H2M and the
  jury panel.
- A selected-hand owner change invalidates HaMeR/ViTPose/registration and the
  jury panel.
- Hunyuan receives the object-only carrier. MoGe deliberately retains the
  joint carrier because it supplies the common observation-space scene.
- Inventory closure proves files and hashes; Q1/Q2 proves semantic quality.
- Implementation/configuration defects are repaired before jury accounting.
- A valid Q1 PASS is the only direct front-half authority for Gate A.

## Downstream route

Gate A -> frame I -> Gate C -> D0 -> H0 -> H1 -> O0 -> J0 -> F0 -> export -> metrics.


## Q1 multiview evidence-presentation correction

Run 233 Q1 is preserved but accounted as
`INVALIDATED_BY_EVIDENCE_PRESENTATION_CONTRACT`. Cell F contained one mesh
asset rendered as three unlabeled orthographic projections. The jury described
the XY / XZ / YZ columns as disconnected fragments. The corrected panel labels
each view, separates the columns, and reports mesh statistics. It does not
change or regenerate any foundation artifact. A replacement Q1 judges the same
hash-owned inventories; Q2 remains unused.
