# Gate D1 independent physical adjudication query

Review the exact current case using:
- original RGB/crop;
- frozen Gate-D0 contract;
- before/after renders;
- selected-contact distances;
- forbidden-contact distances;
- penetration/collision metrics;
- valid depth and z-order evidence;
- object topology/part-state receipts.

Return exactly one decision: `accept`, `reject`, or `review_required`.

Questions:
1. Did the intended finger-part contact occur on the allowed patch?
2. Did any forbidden contact appear?
3. Is the hand on the correct side of the articulated part?
4. Is there visible or measured penetration?
5. Did object topology, articulation, scale, or pose regress?
6. Is the accepted result physically more plausible than the rollback state?

Do not certify a result from scalar loss alone.
