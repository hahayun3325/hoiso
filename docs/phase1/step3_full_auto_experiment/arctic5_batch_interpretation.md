# ARCTIC-5 automatic comparison batch interpretation

## Overall gate counts

| method                | selector_v4_gate          |   count |
|:----------------------|:--------------------------|--------:|
| default_baseline      | reject_severe_floating    |       2 |
| default_baseline      | reject_severe_penetration |       3 |
| old_gpt55_selector_v1 | reject_severe_floating    |       2 |
| old_gpt55_selector_v1 | reject_severe_penetration |       3 |
| partaware_v2_attempt0 | reject_severe_floating    |       2 |
| partaware_v2_attempt0 | reject_severe_penetration |       3 |

## Case-level observations

### abox01

| method                |   object_cd_mm |   object_f5 |   object_f10 |   contact_p5_mm |   hand_inside_object_ratio |   components | selector_v4_gate          | final_status            |
|:----------------------|---------------:|------------:|-------------:|----------------:|---------------------------:|-------------:|:--------------------------|:------------------------|
| default_baseline      |        98.4017 |  0.0119194  |    0.0435863 |       117.221   |                   1        |           15 | reject_severe_penetration | rejected_by_selector_v4 |
| old_gpt55_selector_v1 |       116.597  |  0.0247895  |    0.0673027 |         4.48662 |                   0.249357 |           56 | reject_severe_penetration | rejected_by_selector_v4 |
| partaware_v2_attempt0 |        95.43   |  0.00448249 |    0.0184422 |       120.229   |                   1        |            6 | reject_severe_penetration | rejected_by_selector_v4 |

**Decision:** no safe final replacement yet; send to fallback/contact-aware guidance.

### aket01

| method                |   object_cd_mm |   object_f5 |   object_f10 |   contact_p5_mm |   hand_inside_object_ratio |   components | selector_v4_gate          | final_status            |
|:----------------------|---------------:|------------:|-------------:|----------------:|---------------------------:|-------------:|:--------------------------|:------------------------|
| default_baseline      |       126.417  |   0         |    0         |       398.225   |                   0        |           10 | reject_severe_floating    | rejected_by_selector_v4 |
| old_gpt55_selector_v1 |        40.1763 |   0.0157069 |    0.0447913 |       102.495   |                   0        |           48 | reject_severe_floating    | rejected_by_selector_v4 |
| partaware_v2_attempt0 |        64.5185 |   0.0297329 |    0.0621226 |         6.11554 |                   0.371465 |          219 | reject_severe_penetration | rejected_by_selector_v4 |

**Decision:** no safe final replacement yet; send to fallback/contact-aware guidance.

### alapuse01

| method                |   object_cd_mm |   object_f5 |   object_f10 |   contact_p5_mm |   hand_inside_object_ratio |   components | selector_v4_gate          | final_status            |
|:----------------------|---------------:|------------:|-------------:|----------------:|---------------------------:|-------------:|:--------------------------|:------------------------|
| default_baseline      |        60.5095 |   0.0646981 |   0.124126   |         8.31649 |                 0.0861183  |           47 | reject_severe_penetration | rejected_by_selector_v4 |
| old_gpt55_selector_v1 |        71.4558 |   0.0715335 |   0.135533   |         1.88134 |                 0.33419    |           96 | reject_severe_penetration | rejected_by_selector_v4 |
| partaware_v2_attempt0 |       118.692  |   0.0044142 |   0.00922865 |        13.1895  |                 0.00128535 |          103 | reject_severe_penetration | rejected_by_selector_v4 |

**Decision:** no safe final replacement yet; send to fallback/contact-aware guidance.

### amicuse01

| method                |   object_cd_mm |   object_f5 |   object_f10 |   contact_p5_mm |   hand_inside_object_ratio |   components | selector_v4_gate          | final_status            |
|:----------------------|---------------:|------------:|-------------:|----------------:|---------------------------:|-------------:|:--------------------------|:------------------------|
| default_baseline      |        65.5713 |   0.0726961 |  0.150791    |         4.82265 |                  0.25964   |          161 | reject_severe_penetration | rejected_by_selector_v4 |
| old_gpt55_selector_v1 |        64.5509 |   0.0505892 |  0.102252    |         8.05331 |                  0.0321337 |          264 | reject_severe_penetration | rejected_by_selector_v4 |
| partaware_v2_attempt0 |       146.709  |   0         |  0.000327022 |       129.432   |                  0         |          111 | reject_severe_floating    | rejected_by_selector_v4 |

**Decision:** no safe final replacement yet; send to fallback/contact-aware guidance.

### ascis01

| method                |   object_cd_mm |   object_f5 |   object_f10 |   contact_p5_mm |   hand_inside_object_ratio |   components | selector_v4_gate       | final_status            |
|:----------------------|---------------:|------------:|-------------:|----------------:|---------------------------:|-------------:|:-----------------------|:------------------------|
| default_baseline      |       139.274  |           0 |            0 |         160.96  |                          0 |           64 | reject_severe_floating | rejected_by_selector_v4 |
| old_gpt55_selector_v1 |        92.4054 |           0 |            0 |         130.565 |                          0 |           11 | reject_severe_floating | rejected_by_selector_v4 |
| partaware_v2_attempt0 |       117.704  |           0 |            0 |         155.302 |                          0 |          127 | reject_severe_floating | rejected_by_selector_v4 |

**Decision:** no safe final replacement yet; send to fallback/contact-aware guidance.

## Main conclusion

The batch infrastructure works, but no candidate currently passes the selector-v4 physical gate. Prompt refinement improves some object geometry results, especially aket01, but physical validity still requires attempt1 fallback or contact-aware guidance.
