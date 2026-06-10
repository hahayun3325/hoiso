# Phase 0.17 — ARCTIC Default-vs-Selector Status

## Current achievement

The five selected ARCTIC cases now have prediction pairs:

- default run
- GPT-5.5 + selector-native v2 run

The pair verifier reports final hand and object meshes for both methods.

## Important caution

A default baseline must be checked for selector-path pollution.

A suspicious default log previously contained selector/debug export lines, including paths pointing to a GPT-5.5 selector run. Therefore, before using the default outputs as a fair baseline, we must verify that clean default logs contain no selector/debug lines.

## Current qualitative observation

The default-vs-selector panel is useful for failure-mode analysis:

- `abox01`: default appears to have transform/visibility issues; selector keeps more box-like geometry but still fragmented.
- `aket01`: both mostly fail to reconstruct the bottle body.
- `ascis01`: default drifts to table-like geometry; selector is closer to scissors but fragmented.
- `alapuse01`: default separates screen/body; selector is still blurred/fragmented.
- `amicuse01`: both collapse.

## GT status

ARCTIC GT annotations and object meshes have not been found in the current local paths.

Therefore, ARCTIC is not ready for paper-like quantitative evaluation yet.

## Next steps

1. Verify clean default baseline logs.
2. If polluted, rerun clean default baselines with selector variables explicitly disabled.
3. Use ARCTIC panel for qualitative failure analysis only.
4. Inspect official ARCTIC repo docs/download scripts to locate/install GT annotations and object meshes.
5. Start paper-like ARCTIC metrics only after GT hand/object/camera annotations are available and visually validated.
