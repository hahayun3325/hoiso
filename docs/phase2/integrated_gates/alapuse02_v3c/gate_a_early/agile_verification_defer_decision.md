# AGILE verification timing decision

Decision:
  DEFER_AGILE_VERIFICATION_UNTIL_AFTER_CORE_GATES

Reason:
  The immediate goal is to obtain the first core Gate A/B/C/D result.
  AGILE-style LLM/VLM verification is valuable, but it is a robustness layer,
  not the current bottleneck.

Use now:
  - deterministic mask sanity checks
  - white-background checks
  - component count
  - watertightness / boundary-edge checks
  - visual part-split audit

Use later:
  - VLM/LLM verification of object pose
  - mask correctness check
  - part split plausibility check
  - whether the reconstructed object is safe for optimization

Status:
  Deferred by design, not forgotten.
