# Smoke 022 — Freeze Object Pose and Noise Negative Result

## Goal

Test whether freezing both object-noise learning rates and object pose learning rates prevents final object fragmentation.

## Verified settings

FOHO_NOISE_OBJ_LR1=0.0
FOHO_NOISE_OBJ_LR2=0.0
FOHO_OBJ_LR_SCALE=0.0
FOHO_OBJ_2HALF_LR_SCALE=0.0

## Result

Smoke 022 completed successfully, but the object remained fragmented.

## Evidence

smoke015_hunyuan_initial:
1 component, fragmentation_score = 0.000000

smoke019_exported_obj:
6 components, fragmentation_score = 5.514633

smoke021_exported_obj:
4 components, fragmentation_score = 3.458513

smoke022_exported_obj:
4 components, fragmentation_score = 3.458513

## Interpretation

Freezing object pose and object-noise learning rates is not sufficient.

The fragmentation is likely created earlier inside the final guided latent/SDF/FlexiCubes extraction path.

Pose freezing cannot recover the object once the SDF/mesh itself is already fragmented.

## Conclusion

The next practical solution should be confidence-guided object fallback plus local contact refinement:

- select the best object source by completeness,
- preserve the selected object geometry,
- optimize object SE(3) pose and hand/contact alignment,
- reject final guided object if completeness gets worse.  
