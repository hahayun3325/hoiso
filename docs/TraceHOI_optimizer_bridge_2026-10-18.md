# TraceHOI visual initializer to optimizer bridge

The S3 initializer places the selected right hand relative to the laptop using the exact RGB crop, independent 2D keypoints, saved HaMeR geometry, hand bounding box, and learned MoGe depth. Contact is a later rectified-flow optimization responsibility. Neither a contact score nor collision clearance changes this initial pose.

The saved FollowMyHold optimizer transforms a hand around its axis-aligned bounding-box center. For the column-vector affine map `v_scene = s R v_native + t` and native bounding-box center `c`, the equivalent centered translation is `t_centered = t + s R c - c`. The bridge exports the positive scale, normalized quaternion in wxyz order, and centered translation, and verifies all 778 vertices against the saved initial mesh. A second route uses the already placed scene mesh with identity parameters. The two routes must never be combined.

Both routes require an explicit opt-in backend seam that bypasses the older hand Hunyuan-to-MoGe transform and preserves the supplied visual initialization instead of resetting or re-running phase 1. Original MANO parameters remain unchanged; an external transform owns scene placement. Object geometry stays byte-identical.

This change implements a CPU state converter, immutable portable packet, CLI, and round-trip tests. It does not import, patch, wire or execute the native optimizer. The manual server step captures two known backend Python files as text, with static function/call summaries, for the next integration change. Static source observation is not a runtime test. Current backend compatibility remains pending review of that returned source.

`initialization_ready` remains true; `backend_execution_ready`, `rectified_flow_executed`, `placement_ready`, and `full_parent_acceptance` remain false. Human visual review is complete. Independent mask reference, metric scale, contact and final geometric accuracy remain unresolved; none is treated as a reason to distort the visual initializer.

Open the generated `index.html` for the two-route comparison, and `scene.html` for the initialized hand/laptop scene. Preserve original human review JSON, original inputs, current packets, terminal guards, and complete archives. Archive and Trash only the explicitly verified previous S3 working tree after publication and replacement verification.
