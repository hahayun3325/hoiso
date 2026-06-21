# ARCTIC-5 contact optimization target summary

## Target type counts

| target_type                                   |   count |
|:----------------------------------------------|--------:|
| contact_attraction_and_pose_reposition        |       1 |
| penetration_resolution_and_contact_refinement |       4 |

## Penetration/contact refinement targets

| case      | source_method         | warning_tags                                                                                                                                |
|:----------|:----------------------|:--------------------------------------------------------------------------------------------------------------------------------------------|
| abox01    | old_gpt55_selector_v1 | object_inside_hand_warning;hand_inside_object_warning;object_penetration_depth_warning;hand_penetration_depth_warning                       |
| aket01    | partaware_v2_attempt0 | hand_inside_object_warning;object_penetration_depth_warning;hand_penetration_depth_warning;fragmentation_warning                            |
| alapuse01 | default_baseline      | object_penetration_depth_warning;hand_penetration_depth_warning                                                                             |
| amicuse01 | default_baseline      | object_inside_hand_warning;hand_inside_object_warning;object_penetration_depth_warning;hand_penetration_depth_warning;fragmentation_warning |

## Contact attraction / repose targets

| case    | source_method         | warning_tags                           |
|:--------|:----------------------|:---------------------------------------|
| ascis01 | old_gpt55_selector_v1 | floating_warning;low_integrity_warning |
