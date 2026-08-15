# Phase 0.17 — Prompt Template and Selector Comparison Plan

## Main contributions this week

### 1. Prompt template

The prompt template improves the object description used by the inpainting stage.

A weak prompt can cause semantic or shape drift before 3D reconstruction starts.

### 2. Confidence-guided selector

The selector compares object candidates and chooses the more reliable source.

It is not a hard-coded fallback to Hunyuan. It can choose Hunyuan when final guidance fragments the object, and it can choose the final object when final guidance improves completeness.

## Figure set for weekly report

### Figure 1 — HO3D SPAM prompt and selector diagnosis

Use:

smoke013_015_016_017_comparison_sheet.jpg
Purpose:

- default prompt vs structured prompt,
- rounded can vs boxy SPAM prior,
- final guidance fragmentation,
- motivation for selector.

### Figure 2 — Official OakInk split000 result

Use:

oakink_000_visual_selector_sheet.jpg

Purpose:

- official dataset smoke test,
- vague prompt "A spray bottle",
- hybrid inpainted object,
- selector chooses final object because final object has better completeness.

### Figure 3 — ARCTIC candidate sheet

Use:

arctic_candidate_sheet.jpg

Purpose:

- choose official samples for next runs,
- rigid box/bottle,
- thin scissors,
- articulated laptop/microwave use cases.

## Recommended official samples

### Prompt template

ARCTIC box_grab_01ARCTIC ketchup_grab_01OakInk spray bottle / bottle-like object

### Selector

ARCTIC scissors_grab_01ARCTIC laptop_use_01ARCTIC microwave_use_01HO3D SPAM smoke015–022OakInk split000

## Important ARCTIC note

ARCTIC has 9 camera views stored in folders `0` to `8`.

For articulation, prefer `use` sequences instead of only `grab` sequences:

laptop_use_01/0/00114.jpgmicrowave_use_01/0/00152.jpg
