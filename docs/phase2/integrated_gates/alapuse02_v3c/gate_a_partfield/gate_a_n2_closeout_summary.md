# alapuse02_v3c Gate A N=2 closeout summary

Decision:
  PASS_PARTFIELD_SCREEN_BASE_SPLIT_PARTIAL

What passed:
  - Clean object-only Hunyuan mesh was used as Gate A input.
  - PartField inference and clustering completed.
  - N=2 was selected after visual comparison.
  - Cluster 6876 maps to screen_lid.
  - Cluster 16536 maps to keyboard_base.
  - Named meshes were exported successfully:
      screen_lid.ply
      keyboard_base.ply
  - Final colored scene shows a clean screen/base decomposition.

What this proves:
  This is the first real, non-smoke-test part-aware Gate A result on an
  articulated object in this project.

What it does not prove:
  - hinge recovered as an independent mesh
  - full articulation solved
  - contact-aware optimization solved
  - final Gate C/D readiness for this case

N=3 / N=4 decision:
  Rejected for current Gate A. N=3 over-splits the base; N=4 over-segments
  the object further. N=2 is the cleanest semantic split for the current goal.

Hinge handling:
  Hinge is deferred. If needed later, derive it geometrically from the
  screen_lid / keyboard_base boundary rather than forcing it through
  unsupervised over-clustering.

Next:
  - Use this as the Gate A articulated-object result.
  - Start Gate B contact proposal using screen_lid and keyboard_base.
  - Do not run final Gate C/D on this case until a valid shared hand-object
    3D frame is recovered.
