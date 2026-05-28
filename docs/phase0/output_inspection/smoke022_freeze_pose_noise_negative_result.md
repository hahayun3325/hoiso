# Smoke 022 — Freeze Object Pose and Noise Negative Result

## Goal

Test whether freezing both object-noise learning rates and object pose learning rates prevents final object fragmentation.

## Verified settings

FOHO_NOISE_OBJ_LR1=0.0
FOHO_NOISE_OBJ_LR2=0.0
FOHO_OBJ_LR_SCALE=0.0
FOHO_OBJ_2HALF_LR_SCALE=0.0

The params file confirms:

obj_lrs = {"scale": 0.0, "trans": 0.0, "rot": 0.0}obj_2half_lrs = {"scale": 0.0, "trans": 0.0, "rot": 0.0}noise_obj_lr1 = 0.0noise_obj_lr2 = 0.0

## Result

Smoke 022 completed successfully, but the object remained fragmented.

## Evidence

smoke015_hunyuan_initial:1 component, fragmentation_score = 0.000000smoke019_exported_obj:6 components, fragmentation_score = 5.514633smoke021_exported_obj:4 components, fragmentation_score = 3.458513smoke022_exported_obj:4 components, fragmentation_score = 3.458513

## Interpretation

Freezing object pose and object-noise learning rates is not sufficient.

The fragmentation is likely created earlier inside the final guided latent/SDF/FlexiCubes extraction path.

Pose freezing can prevent wrong object movement, but it cannot recover object surfaces that are already disconnected.

## Next direction

Use confidence-guided object fallback plus local contact refinement:

1. select the best object source by completeness,
2. reject fragmented final guided object,
3. preserve selected object geometry,
4. align it to the final hand using object SE(3),
5. apply local contact refinement without changing global object shape.  
