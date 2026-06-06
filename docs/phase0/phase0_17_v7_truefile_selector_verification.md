# Phase 0.17 — V7 True Phase 4.2 Selector Verification

## Run

`oakink000_gpt55_short_selector_auto_frag_export_v7_truefile`

## Main result

The automatic internal selector is now functionally verified.

The selector compares:

1. `before_phase42`
2. `phase42_before_joint_true`

and passes the selected object state to the following joint hand-object alignment stage.

## Evidence

### Selector decision

before_frag=23.023389
current_frag=34.044994
selected=before_phase42

### File identity check


before_phase42 hash:66454c4a2795eb404124bb11c02a061dphase42_before_joint_true hash:32285284fd028f60af3dce3788776176selected_before_joint hash:66454c4a2795eb404124bb11c02a061d


This means:


before_phase42 != phase42_before_joint_trueselected_before_joint == before_phase42


## Interpretation

Phase 4.2 made the object candidate more fragmented for this GPT-5.5 OakInk split000 run.

The selector correctly rejected the worse Phase 4.2 candidate and restored the cleaner before-Phase-4.2 object state before Phase 4.3 joint alignment.

## Remaining limitation

The debug panel uses normalized object-view rendering for candidate meshes. This is useful for shape and fragmentation comparison, but it is not a perfect camera-aligned rendering against the input image.

For final report figures, use the panel as selector-mechanism evidence, not as exact 2D alignment evidence.  
