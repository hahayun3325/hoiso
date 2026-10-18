# Fresh runtime inputs for joint rectified-flow

The opt-in U5 handoff preserves the CPU visual initial hand pose, but the native loop still expects legacy masks, a scene mesh and a pickle-style HaMeR file. V6 prepares explicit fresh-scene data without executing native dependencies or a model.

The new `runtime_inputs` API and CLI bind the saved U5 handoff, N7 observation, P8 object fit, HaMeR prediction and original image. Every native object vertex is transformed and compared with the unchanged scene object. The integer-pixel camera is checked against fresh intrinsics; every supported depth point is reprojected to its original pixel. Original exclusive hand/object masks and ambiguous boundary mask are retained, alongside separately named validity-intersected masks.

A partial observation mesh uses two fixed triangles per image cell, only across valid same-class pixels with relative depth jump at most 2%. This is a rendering proxy, not a closed collision surface. A numeric float32 object matrix and HaMeR keypoints are exported without pickle. The legacy `.item()` loader must not consume these files; a numeric loader adapter is still required. HaMeR keypoints remain model predictions, distinct from the independent ViTPose targets.

CPU initialization remains visual, bounding-box, HaMeR and fresh-depth based. No contact or collision score changes the initial pose. Contact is deferred to the later joint rectified-flow stage. Native renderer pixel centers/normals, object conditioning and latent initialization policy, tensor/assets and bounded model execution remain pending. Final placement and independent mask accuracy are not claimed.

Validation: 28 focused contract tests plus the existing 421 tests; before/after installation checks recompute the real packet, compare exact bytes and refuse placement purpose. The manual server carrier checks the U5 base, publishes five exact additions with a normal push, then archives and Trashes only the verified U5 tree. Original terminal guards, evidence archives, human review records and original inputs remain protected.
