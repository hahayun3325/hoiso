# Phase 0.17 — ARCTIC Default Runs and Evaluation Status

## Current status

GPT-5.5 + selector-native v2 outputs exist for the five selected ARCTIC samples.

Default run directories and configs exist, but the default folders were initially empty. Therefore, the default baselines still need to be run before fair default-vs-selector comparison.

## Important clarification

`baseline_existing` in the manifest only means the folder exists. It does not guarantee that final hand/object meshes exist.

A valid baseline requires:

- `guidance_out/<case>_hand.ply`
- `guidance_out/<case>_obj.ply`
- final native render under `foho_debug`

## GT status

The current FollowMyHold repo does not include a complete ARCTIC GT evaluator/loader.

The local ARCTIC dataset path did not reveal the needed GT annotation or mesh files in the first search. A deeper ARCTIC GT layout inspection is needed before paper-like quantitative metrics can be computed.

## Next steps

1. Repair default configs with explicit output paths.
2. Run one default proof case, starting with `abox01_default`.
3. Verify default final meshes.
4. Run all default baselines.
5. Generate default-vs-selector qualitative panel.
6. Resolve ARCTIC GT annotations/meshes separately before paper-like metrics.
