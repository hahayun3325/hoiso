# v88 Residual-Geometry and Next-Family Selection Toolkit

This toolkit is read-only. It freezes the v87 rejection, separates **subspace insufficiency** from **bound/linearization insufficiency**, audits per-joint residual morphology, and writes a non-authorizing next-family recommendation.

It does not run MANO, move a mesh, alter v87 artifacts, collect new derivatives, or authorize optimization.

## Main outputs

- `v87_input_verification.json`
- `residual_geometry_report_v88.json`
- `per_joint_residuals_v88.csv`
- `next_family_route_v88.json`
- `next_family_route_v88.md`

## Scientific distinction

The v87 bounded residual and the unbounded least-squares residual answer different questions:

- a large **bounded-to-unbounded gap** indicates a bound or local-linearization limitation;
- a large **unbounded residual floor** indicates a missing subspace, wrong candidate, or observation mismatch.

The route writer never authorizes an optimizer.
