# alapuse02_v3c Gate A PartField N2 result decision

Decision:
  PASS_PARTFIELD_SCREEN_BASE_SPLIT_PARTIAL

Evidence:
  - Clean object-only Hunyuan mesh used as Gate A input.
  - PartField inference and agglomerative clustering completed.
  - N=2 selected: screen_lid (cluster 6876) and keyboard_base (cluster 16536),
    both IDs visually confirmed correct.

N=3 investigated and explicitly rejected:
  - Hypothesis: N=3's third cluster might be a recovered hinge bracket.
  - Bbox-extent check disproved this: all three N=3 clusters share close to
    full-object extent in two of three dimensions (screen: [0.16,1.65,1.99];
    base-piece-1: [1.87,0.14,1.99]; base-piece-2: [1.93,0.18,1.99]).
  - This is consistent with N=3 splitting the flat base slab into two
    similarly-sized panels (e.g. top/bottom faces), not isolating a small
    hinge fragment.
  - A real hinge bracket would be small relative to the full mesh; none of
    the N=3 clusters show that signature.

Hinge handling:
  - Hinge is NOT recovered as a PartField cluster and this is not being
    pursued further via higher N.
  - Hinge is not required for the immediate Gate C (contact) goal, since
    hand-object contact occurs on screen_lid/keyboard_base surfaces.
  - If needed later for kinematic/articulation modeling, derive the hinge
    axis geometrically from the screen_lid/keyboard_base boundary, not from
    unsupervised over-clustering.

Interpretation:
  This is the first real, non-smoke-test PartField-based part split for
  alapuse02_v3c: a genuine two-part decomposition of an articulated object.

Do not claim:
  - hinge geometry recovered
  - full articulation solved
  - contact/optimization readiness (Gate C/D still pending, and the
    separate guided-diffusion shared-frame issue from earlier remains
    unresolved for this case)

Next:
  - run quality/coverage report on the N=2 parts
  - prepare Gate A comparison panel for documentation
