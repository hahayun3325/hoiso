# alapuse02_v3c PartField N-selection decision

Decision:
  SELECT_N2_AS_PRIMARY_GATE_A_SPLIT

Evidence:
  - N=2 cleanly separates the open laptop into two meaningful physical parts:
      screen_lid
      keyboard_base
  - N=3 further splits the base, which is unnecessary for the current Gate A.
  - N=4 begins to split the screen/lid, which is over-segmentation.
  - Therefore N=2 is the best semantic part split for the current research goal.

Interpretation:
  This is the first real PartField-based articulated-object part split for
  alapuse02_v3c. It is not just an I/O smoke test.

Caveat:
  The hinge is not separately recovered as its own mesh. For now, represent
  the hinge as a derived boundary / joint axis between screen_lid and
  keyboard_base.

Decision label:
  PASS_PARTFIELD_SCREEN_BASE_SPLIT_PARTIAL

Next:
  Export N=2 clusters as named parts and create a manifest/scene for Gate A.
