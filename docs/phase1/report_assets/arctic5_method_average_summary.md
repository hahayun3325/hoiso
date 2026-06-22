# ARCTIC-5 method average summary

| method                        |   object_cd_mm |   object_f10 |   contact_p5_mm |   hand_inside_object_ratio |
|:------------------------------|---------------:|-------------:|----------------:|---------------------------:|
| default_baseline              |         98.035 |        0.064 |         137.909 |                      0.269 |
| old_gpt55_selector_v1         |         77.037 |        0.07  |          49.496 |                      0.123 |
| partaware_v2_attempt0         |        108.611 |        0.018 |          84.854 |                      0.275 |
| selector_v41_refined_pipeline |         97.061 |        0.037 |          61.355 |                      0.305 |

Lower is better for `object_cd_mm`, `contact_p5_mm`, and `hand_inside_object_ratio`; higher is better for `object_f10`.
