# Gate D0 targeted semantic query

You are reviewing one current, provenance-bound hand–articulated-object reconstruction case.

Inputs:
- exact current RGB/crop;
- accepted Gate-B semantic receipt;
- labeled Gate-A part/side overlay;
- indexed current hand/finger overlay;
- optional valid depth visualization.

Determine **only** the missing semantic fields needed to compile an executable contact contract.

1. Which Gate-B candidate fingers are visibly supported as likely contact fingers?
2. For each supported finger, which named object part and side/region is the plausible target?
3. Which proposed fingers or target regions remain uncertain?
4. Which nearby named regions should explicitly remain forbidden?
5. What front/back or z-order relation is expected at the visible contact region?
6. Is contact expected, near-contact acceptable, or no-contact?

Rules:
- Do not invent MANO vertex IDs, joint IDs, Gate-A face IDs, or numeric transforms.
- Do not rename object parts outside the provided inventory.
- Prefer `review_required` over unsupported certainty.
- Return JSON matching `gate_d0_semantic.schema.json`.
