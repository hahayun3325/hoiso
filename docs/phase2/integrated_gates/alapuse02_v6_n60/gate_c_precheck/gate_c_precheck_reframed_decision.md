# alapuse02v6n60 Gate C precheck -- reframed methodology

Architectural note:
  guidance.run's joint hand+object optimizer has no gate-awareness --
  it is not constrained by Gate A's verified object shape or Gate B's
  contact hypotheses. This is a structural explanation for why
  guidance_out's object branch has now independently corrupted geometry
  in both alapuse02_v3c and alapuse02v6n60: the optimizer has no
  objective term that penalizes deviating from gate-verified ground
  truth.

Methodology change:
  Gates should be tested against the PRE-OPTIMIZATION composition
  (trustworthy guidance_out hand + freshly h2m-aligned Gate A object
  pose), not against guidance.run's joint-optimized output. This is
  consistent with the professor's earlier gate-ordering principle:
  Gate C should act as a precondition on optimization, not only a
  post-hoc check on it.

Current state:
  The bypass-composed frame (hand + h2m-aligned screen_lid/keyboard_base)
  shows visible hand-object interpenetration. Per this project's own
  precedent (aket01's Gate D: PASS_PROXY_PUSHOUT_REDUCES_COLLISION_
  KEEP_CONTACT), some interpenetration in a raw pre-repair composition
  is expected and is specifically what Gate D's collision-repair logic
  exists to resolve -- it is not automatically a shared-frame failure.

Decision:
  Do not freeze on penetration alone. Proceed to:
    1. quantify actual penetration depth (signed-distance check);
    2. attempt one bounded Gate D proxy push-out repair, reusing
       aket01's approach, targeting reduced penetration while
       preserving the Gate B contact hypothesis.
