# ARCTIC-5 selector-v4.1 full-pipeline rerun summary

| case      |   object_cd_mm |   object_f10 |   contact_p5_mm |   hand_inside_object_ratio |   largest_component_fraction |   relative_object_center_error_mm |   relative_pose_delta_vs_baseline_mm | selector_v4_gate          | main_read                                                                 |
|:----------|---------------:|-------------:|----------------:|---------------------------:|-----------------------------:|----------------------------------:|-------------------------------------:|:--------------------------|:--------------------------------------------------------------------------|
| abox01    |         93.884 |        0.069 |         174.971 |                      1     |                        0.737 |                           193.202 |                              -29.257 | reject_severe_penetration | Object shape improves, but hand remains inside box.                       |
| aket01    |         75.619 |        0.074 |           3.14  |                      0.515 |                        0.937 |                           135.222 |                              -27.812 | reject_severe_penetration | Best positive case: contact and F-score improve, but penetration remains. |
| ascis01   |         93.441 |        0     |          70.096 |                      0     |                        0.928 |                           145.805 |                                0.859 | reject_severe_floating    | Thin scissors remain hard; contact improves but object still floats.      |
| alapuse01 |        121.216 |        0.004 |           9.812 |                      0.005 |                        0.518 |                           160.912 |                               18.027 | reject_severe_penetration | Visual pose may look meaningful, but GT and relative metrics worsen.      |
| amicuse01 |        101.148 |        0.036 |          48.755 |                      0.005 |                        0.677 |                           172.155 |                                8.513 | reject_severe_penetration | Microwave remains fragmented / poorly aligned; articulated case is hard.  |

## Main conclusion

Selector-v4.1 full-pipeline rerun is technically successful and gives partial improvements, especially on `aket01`. However, it does not consistently improve all ARCTIC-5 cases. The remaining failures motivate part-wise object reconstruction and contact-aware optimization.
