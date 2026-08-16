# Automatic contact-patch radius selection

Generated: 2026-08-16T02:46:41.045783+00:00

After a semantic model identifies the object contact region, geometry selects
the metric patch. A candidate must satisfy topology/projection checks, at least
90% precision
inside the semantic ROI, and at least
50% ROI coverage. The
smallest feasible radius is selected. If none is feasible, the pipeline
returns REVIEW_REQUIRED; it does not choose the largest patch.

The VLM owns semantic locality, not triangle radius or face IDs. Thresholds
are globally preregistered and should be reported in sensitivity ablations.
For alapuse02v3n60 this policy independently reproduces r04.
