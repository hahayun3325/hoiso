# alapuse02v6n60 Gate A N=2 closeout

Decision:
  PASS_GATE_A_PARTFIELD_N2_SCREEN_BASE_SPLIT

Selected PartField candidate:
  N=2

Semantic mapping:
  cluster 29330 -> screen_lid
  cluster 26183 -> keyboard_base

Face assignment:
  screen_lid = 9386 faces
  keyboard_base = 20614 faces
  total = 30000 / 30000 source faces

Why N=2 was selected:
  - clean separation of the two meaningful rigid laptop parts;
  - screen/lid remains one complete articulated link;
  - keyboard/base remains one complete articulated link;
  - simpler and more physically meaningful than N=3 or N=4.

N=3 interpretation:
  - screen/lid remains separate;
  - keyboard/base is divided into keyboard/deck and base shell.
  - retained only as a diagnostic.

N=4 interpretation:
  - screen and base are subdivided further into surface-level regions.
  - retained only as an over-segmentation diagnostic.

Hinge:
  not recovered as an independent mesh.
  If required, derive the hinge axis later from the boundary between
  screen_lid and keyboard_base.

Limitation:
  Gate A proves part decomposition for this case.
  It does not yet prove a valid shared hand-object frame or contact
  optimization.

Next:
  create a conservative image-based Gate B proposal.
