# HOISO-Flow abstract draft

Monocular reconstruction of hand-articulated-object interactions commonly
combines foundation models whose outputs differ in geometry, scale, coordinate
frame, and semantic reliability. A locally plausible upstream error can
therefore propagate into physically invalid hand-object alignment. We propose
HOISO-Flow, a verification-gated reconstruction pipeline that treats
foundation-model predictions as evidence rather than unquestioned state. The
pipeline uses an upstream evidence gate to localize and reopen failed branches,
a part-aware object stage to preserve articulated structure, and hash-owned
coordinate contracts to initialize trusted object and hand assets in a shared
MoGe frame. It then performs staged hand and object refinement. Coarse contact
proposals are compiled into an executable Gate-D0 contract linking selected
MANO fingers to localized, allowed object-part surfaces while specifying
forbidden contact, occlusion, and collision constraints. An independent
Gate-D1 adjudicator verifies the refined interaction and prevents loss
reduction from masking geometric regressions. The resulting design targets
three problems: containment of upstream errors, part-aware articulated object
recovery, and verified semantic-to-geometric contact refinement. We will
evaluate reconstruction accuracy, contact localization, penetration, failure
containment, wall-clock time, and peak GPU memory under matched baselines.
Efficiency and alignment superiority are treated as empirical questions rather
than assumed claims.

Status: research-plan draft. Do not claim faster runtime, lower memory, or
superior alignment until matched measurements and ablations are complete.
