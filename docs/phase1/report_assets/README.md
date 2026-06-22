# Phase 1 report assets

This folder organizes the assets for the Phase 1 refined selector report.

## Meshes

`meshes/<case>/<method>/`

Each method folder contains:

- `final_hand.ply`
- `final_object.ply`
- `final_hoi_colored.ply`
- `final_hoi_scene.glb`

Methods:

- `baseline`
- `selector_gpt55`
- `selector_v41`

## Inpainting images

`inpainting/<case>/<method>/`

Each method folder contains:

- `inpaint_selected.png`
- top candidate images copied for manual checking

The contact sheet is:

`inpainting/arctic5_inpainting_contact_sheet.jpg`

## Tables

`tables/arctic5_v41_rerun_summary.md`

Main table for the five ARCTIC cases.

`tables/arctic5_method_average_summary.md`

Average metric table by method.

## Slide note

`slides/new_metrics_explanation_slide.md`

Extra slide explaining the new metrics, especially the relative object-center-to-hand-center error.
