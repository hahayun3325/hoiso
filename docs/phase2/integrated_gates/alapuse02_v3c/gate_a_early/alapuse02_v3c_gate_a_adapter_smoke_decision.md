# alapuse02_v3c Gate A adapter smoke-test decision

Decision:
  PASS_IO_SMOKE_TEST
  FAIL_REAL_PART_SPLIT_NOT_IMPLEMENTED

Evidence:
  - run_gate_a_part_split_adapter.py completed without crashing.
  - part_manifest.json and part_scene.glb were created.
  - However, the manifest exported the full mesh as screen_lid:
      screen_lid vertices = 75,002
      keyboard_base = not exported
      hinge = not exported
      residual_uncertain = not exported

Interpretation:
  The adapter only verifies file loading/export plumbing.
  It does not prove laptop part separation.

Next:
  Run a real Gate A split using PartField + 2D part masks, or a manual
  SAM2 part-mask fallback.
