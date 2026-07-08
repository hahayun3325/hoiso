# alapuse02_v3c Gate B contact proposal v0 decision

Decision:
  PASS_GATE_B_CONSERVATIVE_IMAGE_CONTACT_PROPOSAL

What was created:
  - manual JSON contact proposal
  - CSV summary

Part labels used:
  - screen_lid
  - keyboard_base

Conservative contact hypotheses:
  1. upper visible hand / fingertips -> screen_lid
  2. lower visible hand / fingertips -> keyboard_base

Negative / low-confidence hypotheses:
  - upper visible hand -> keyboard_base is not the primary contact
  - lower visible hand -> screen_lid is not the primary contact

Important caveat:
  This is only a semantic/image-based Gate B proposal.
  It should not be used as an optimization target until Gate C verifies it
  with a trusted 3D shared hand-object frame.

Decision label:
  PASS_GATE_B_CONSERVATIVE_IMAGE_CONTACT_PROPOSAL

Next:
  - copy JSON/CSV into docs
  - commit Gate B v0
  - decide whether to recover a trusted shared frame for alapuse02_v3c
    or move Gate C/D demonstration to abox01
