# alapuse02v6n60 Gate B proposal v0

Decision:
  PASS_GATE_B_CONSERVATIVE_IMAGE_CONTACT_PROPOSAL

Gate A parts:
  screen_lid
  keyboard_base

Positive contact hypotheses:
  1. upper visible hand / fingertips -> screen_lid
  2. lower visible hand / fingertips -> keyboard_base

Negative hypotheses:
  - upper visible hand -> keyboard_base is not the primary contact
  - lower visible hand -> screen_lid is not the primary contact

Important limitation:
  This is an image-semantic proposal only.

All contacts remain:
  should_use_for_optimization = false

They must not become optimization targets until Gate C verifies:
  - hand identity;
  - common coordinate frame;
  - metric scale;
  - root pose;
  - nearest surface correspondence;
  - contact rather than depth-projection overlap.

Next:
  perform a shared-frame hand/object provenance audit before Gate C.
