# selector-v4.1 full-pipeline findings summary

## Case-level summary

| case      | best_object_cd_method         | best_object_f10_method        | best_contact_p5_method        |   selector_v41_cd |   selector_v41_f10 |   selector_v41_contact_p5 |   selector_v41_relative_pose_delta_vs_baseline_mm | main_read                                                   |
|:----------|:------------------------------|:------------------------------|:------------------------------|------------------:|-------------------:|--------------------------:|--------------------------------------------------:|:------------------------------------------------------------|
| abox01    | selector_v41_refined_pipeline | selector_v41_refined_pipeline | old_gpt55_selector_v1         |           93.8837 |         0.0692596  |                 174.971   |                                        -29.2569   | object shape improves, but hand remains inside box          |
| aket01    | old_gpt55_selector_v1         | selector_v41_refined_pipeline | selector_v41_refined_pipeline |           75.6188 |         0.0737093  |                   3.1398  |                                        -27.8116   | positive case: best contact/F-score but penetration remains |
| alapuse01 | default_baseline              | old_gpt55_selector_v1         | old_gpt55_selector_v1         |          121.216  |         0.00401725 |                   9.81227 |                                         18.0274   | visual pose may help, but GT/relative metrics worsen        |
| amicuse01 | old_gpt55_selector_v1         | default_baseline              | default_baseline              |          101.148  |         0.0360884  |                  48.7548  |                                          8.51305  | articulated microwave remains fragmented / poorly aligned   |
| ascis01   | old_gpt55_selector_v1         | default_baseline              | selector_v41_refined_pipeline |           93.4407 |         0          |                  70.0964  |                                          0.859163 | thin object still hard; contact improves but still floating |

## Main conclusion

The selector-v4.1 refined-prompt pipeline is a successful full-pipeline integration, but it is not yet a consistent final-HOI improvement. It improves selected cases, especially aket01, while articulated and thin-object cases still require part-aware reconstruction and contact-aware optimization.
