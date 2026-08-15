# Selector Hook Debug Export Plan

Before inserting the selector, add explicit debug exports inside the guidance pipeline:

1. export object before object-focused refinement,
2. export object after object-focused refinement,
3. export object before joint alignment,
4. export object after joint alignment.

Then compare:

- connected components,
- fragmentation score,
- 2D mask fit,
- MoGe point/depth agreement.

The selector should be inserted after the best object-focused candidate is available and before hand-object alignment.
