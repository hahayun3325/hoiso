# v99.8–v99.10 Expanded Gate-C Capacity Toolkit

This toolkit performs the final **read-only** target-reachability test for:

```text
3 translation variables
+ 1 global log hand-scale variable
+ 18 selected articulation variables
= 22 variables
```

It does not call MANO, does not write a nonzero mesh, and never authorizes an optimizer directly.

## Sequence

1. `bootstrap_v99_8.sh` creates fail-closed workspaces and a policy template.
2. Review the exact weighting, translation radius, scale bounds, articulation bounds, and acceptance thresholds.
3. Set `authorizes_capacity_execution` to `true` only after professor/source review.
4. `build_expanded_jacobian_v99_8.py` assembles and audits the 42x22 matrix.
5. `run_expanded_capacity_v99_9.py` runs one deterministic CPU-only mixed-constraint capacity analysis with an optional required SciPy cross-check.
6. `write_v99_10_decision.py` writes a non-authorizing scientific route.

The exact log-scale interval is asymmetric:

```text
log(0.95) <= global_log_hand_scale <= log(1.05)
```

Do not replace it with a symmetric approximation.
