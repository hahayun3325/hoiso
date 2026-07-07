# alapuse02_v3c current Gate A state

Object-only Hunyuan v4:
  PASS_CLEAN_OBJECT_MESH

Evidence:
  - clean open-laptop object mesh
  - screen, base, hinge visually recognizable
  - no hands/arms/background artifacts
  - best laptop geometry so far

Known limitation:
  - right-bottom corner is locally imperfect
  - treat as local reconstruction limitation, not current blocker

Gate A adapter v1:
  PASS_IO_SMOKE_TEST
  FAIL_REAL_PART_SPLIT_NOT_IMPLEMENTED

Reason:
  The adapter exported the whole mesh as screen_lid.
  keyboard_base, hinge, and residual_uncertain were not exported.

Next:
  Run actual part splitting:
    preferred: PartField inference + vmap merge
    fallback: manual/geometric screen-base-hinge split
