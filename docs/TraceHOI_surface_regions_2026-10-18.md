# Connected surface regions — 2026-10-18

The Q9 adaptive pipeline is published at `7c54618ff7a8ac992f0542d3c3bc06898b248d79`. This addition groups its saved adaptive hand cells into connected proximity regions. It leaves all four source meshes, object geometry, masks, transforms and collision gates unchanged.

`surface_regions.py` uses an exact integer barycentric grid through subdivision depth three. Positive-length shared edges connect cells across both matching and unequal subdivision levels, including across original mesh faces. Corner-only touches do not connect cells. Mesh indices define topology; coincident unshared vertices are not welded. Duplicate or nonmanifold source faces are refused. Zero-area and outside-bound cells cannot bridge regions.

A core component contains only positive-area cells whose upper distance bound is within the fixed 2% object-diagonal threshold. A possible region contains core and unresolved cells. Unresolved cells can join several otherwise separated cores. Each possible region reports a lower and upper bound on its total within-threshold area. These values do not bound the area or number of actual connected proximity components. The threshold is a diagnostic distance threshold, not evidence of contact.

The offline region explorer supports candidate and region selection, cell filtering, orbit, cell/witness inspection and JSON export. It retains the exact prior surface map, interval dashboard and independent-reference annotator as companions. Its receipt binds every file and the source map. The CLI rebuilds the result from authenticated inputs and refuses placement purposes.

Thirty-two new topology and region tests cover unequal refinement, reversed edge orientation, point-only touches, uncertain and zero-area bridges, area conservation, malformed topology, determinism and refusal of placement. The manual server carrier runs all 340 portable checks and real-bundle comparisons before and after installing five exact additions. It uses normal Git publication from the recorded Q9 base. Server execution and publication of this step remain pending until its return is verified.

The completed human observation review remains preserved. An independent reference annotation is still absent, so mask accuracy, metric scale, physical contact, geometric accuracy and parent placement remain unverified. All candidates remain diagnostic, including the branch blocked by transverse crossings. No new model call, nearest-surface query location, optimization or mask edit is introduced.

After publication and verified replacement evidence, the carrier archives the complete Q9 working tree, verifies readback, and moves that one tree to recoverable Trash. Original terminals, terminal variants, evidence archives, inputs and human records must be retained. Unknown files stop retirement rather than being discarded. Do not rerun Q9 or this attempt after a partial run; preserve its logs for recovery.
