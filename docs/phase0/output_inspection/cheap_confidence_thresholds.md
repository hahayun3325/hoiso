# Cheap Confidence Thresholds

## Purpose

Run fast object-quality checks after major object-changing stages.

## Object-changing stages

1. after 2D mask / inpainting,
2. after Hunyuan initial mesh,
3. after object guidance,
4. after joint guidance / final export,
5. after fallback selection.

## Rigid object suspicious rules

For rigid objects, a result is suspicious if:

components_final > components_initial + 1
or largest_face_ratio_final < 0.8
or fragmentation_score_final > fragmentation_score_initial + 1.0
or bbox_diag_ratio not in [0.5, 2.0]
or mesh is empty / unreadable

## Articulated object rule

For articulated objects, use expected part count instead of one-component assumption.

C_part = exp(-abs(N_components - N_expected_parts))

## Recommended strategy

Always run cheap confidence after object-changing stages.

Run expensive confidence only when cheap confidence is suspicious.  
