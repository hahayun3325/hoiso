# aket01 object baseline caveat

aket01_obj.ply's dominant component has bbox extents around [0.62, 1.05, 1.04] m,
which is too large for a ketchup bottle alone. The mesh likely includes
support/table or other non-object geometry.

Therefore aket01-derived object/hand ratios should be treated as diagnostic
signals only, not as calibration targets for other cases.
