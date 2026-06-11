# Phase 0.17 — ARCTIC Quantitative Observations

## Scope

This document summarizes quantitative observations for the five manually selected ARCTIC Phase 0.17 samples:

- `abox01`
- `aket01`
- `ascis01`
- `alapuse01`
- `amicuse01`

This should be described as:

**selected-case ARCTIC paper-style evaluation**

not:

**official full ARCTIC benchmark evaluation**

because the current set contains only five manually selected samples.

---

## Evaluation protocols

### 1. Dry-run evaluator

The dry-run evaluator uses raw mesh vertices directly.

It is useful for checking whether the full evaluation path works:

- GT loading
- prediction mesh loading
- hand-based alignment
- object CD / F5 / F10 computation

But it can be biased by mesh tessellation. If one mesh has many vertices in one region, that region can dominate the metric.

### 2. Surface-sampled evaluator

The stricter evaluator samples points uniformly from object mesh surfaces.

This is closer to paper-style evaluation because it evaluates the whole object surface more fairly.

The surface-sampled evaluator still evaluates the same object as the dry-run evaluator. It does not evaluate a different object part. The difference is only how evaluation points are selected.

---

## Main result

Both dry-run and surface-sampled metrics show the same main trend:

**GPT-5.5 + selector improves average object Chamfer Distance.**

### Dry-run average

| method | object CD ↓ | F5 ↑ | F10 ↑ |
|---|---:|---:|---:|
| default | 98.03 mm | 0.0299 | 0.0637 |
| GPT-5.5 + selector | 77.04 mm | 0.0325 | 0.0700 |

The dry-run shows a mean object CD improvement of about **21.00 mm**, or about **21.4%** relative improvement.

### Surface-sampled average

| method | object CD ↓ | F5 ↑ | F10 ↑ |
|---|---:|---:|---:|
| default | 97.28 mm | 0.0382 | 0.0670 |
| GPT-5.5 + selector | 75.32 mm | 0.0375 | 0.0710 |

The surface-sampled result shows a mean object CD improvement of about **21.96 mm**, or about **22.6%** relative improvement.

This means the CD improvement is not only a raw-vertex artifact. It remains after fairer surface sampling.

---

## Per-case observations from surface-sampled metrics

### `aket01` — strongest improvement

The selector strongly improves the ketchup bottle case:

- default CD: **129.25 mm**
- selector CD: **40.53 mm**

This is the clearest positive case. It suggests that the selector helps choose or preserve a better object shape/pose for the bottle.

### `ascis01` — clear CD improvement, but F-score still zero

The selector improves scissors CD:

- default CD: **136.34 mm**
- selector CD: **90.29 mm**

However, F5 and F10 remain zero. This means the selector makes the prediction closer globally, but the geometry is still not accurate enough at strict 5 mm / 10 mm thresholds.

### `amicuse01` — small CD improvement, worse F-score

The selector slightly improves microwave CD:

- default CD: **63.06 mm**
- selector CD: **59.76 mm**

But F5/F10 decrease. This suggests the selector may improve average distance while reducing tight local overlap or surface coverage.

### `abox01` — worse CD, better F-score

The selector worsens box CD:

- default CD: **98.42 mm**
- selector CD: **113.73 mm**

But F5/F10 improve. This means some local regions are closer, but the overall object surface or scale/pose is worse.

### `alapuse01` — worse CD, slightly better F-score

The selector worsens laptop CD:

- default CD: **59.34 mm**
- selector CD: **72.30 mm**

But F5/F10 improve slightly. This is another case where local overlap improves but global object coverage/pose may worsen.

---

## Precision and recall interpretation

In the surface-sampled average, the selector increases precision but decreases recall:

- precision@5mm: **0.0408 → 0.0513**
- recall@5mm: **0.0394 → 0.0301**
- precision@10mm: **0.0726 → 0.1023**
- recall@10mm: **0.0707 → 0.0563**

This means the selector tends to create some predicted surface regions that are closer to GT, but it may cover less of the full GT object surface.

In simple words:

**The selector helps local correctness, but it does not always improve full object completeness.**

---

## Alignment interpretation

Hand CD is almost identical between default and selector because the evaluator aligns predictions to GT using the hand.

Therefore, the current numbers do not prove that the selector improves hand alignment.

The safer conclusion is:

**The selector improves object reconstruction quality after hand-based alignment, but its effect on hand-object alignment should be studied with additional contact or relative-pose metrics.**

---

## Final conclusion

The surface-sampled metrics support the following claim:

**On five selected ARCTIC Phase 0.17 samples, GPT-5.5 prompting plus the internal selector improves mean object Chamfer Distance compared with the default baseline. However, the gains are category-dependent, F-score remains low, and the selector does not consistently improve full object coverage.**

This is a useful Phase 0 result, but it should not be overclaimed as full ARCTIC benchmark performance.
