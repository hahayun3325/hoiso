# abox01 preflight decision

Decision: FAIL_UNTRUSTWORTHY_FRAME_STRUCTURALLY_SIMILAR_TO_ALAPUSE02V3C

## What was checked

guidance_out/abox01_hand.ply and guidance_out/abox01_obj.ply, from the
original (non-bypass) pipeline run -- no realignment or rescue applied.

## Numeric result

Fingertip-to-object min distance = 19.50cm, mean = 23.19cm.
Both above the 12.5cm alapuse01-derived unreachability threshold.

## Visual result

GLB export (hand=red, object=blue) shows no red geometry visible from any
angle: the hand mesh is fully enclosed within the object mesh's volume,
not resting on its surface as in the source photo (where the subject
visibly holds the box with both hands from outside).

## Scale sanity

object/hand bbox ratio = 4.06x (longest axis), up to 7.66x on one axis.
Object longest axis = 2.31m -- implausible for a hand-held wooden box.

## Connected-component diagnostic

Full mesh: 75004 vertices, bbox longest axis 2.31m.
4 connected components found:
  component 0: 53731 verts (71.6% of total), bbox longest axis 2.18m
  component 1: 10861 verts, bbox longest axis ~1.77m
  component 2:  9145 verts, bbox longest axis ~1.64m
  component 3:  1267 verts, bbox longest axis ~0.69m

The dominant component (71.6% of vertices) already reproduces almost the
entire implausible 2.18m scale on its own -- this is not a case of a
correctly-scaled object plus a small amount of extraneous junk geometry.
Filtering to the dominant component alone left the fingertip distance
completely unchanged (min=19.50cm, mean=23.19cm, identical per-fingertip
values to the unfiltered mesh), confirming numerically that no cheap fix
is available here.

## Interpretation

This failure pattern is structurally different from a simple contamination
case (e.g. table geometry riding alongside a correctly-scaled object) and
structurally similar to alapuse02_v3c's deep guidance_out corruption:
a genuinely wrong-scale/malformed object export, not an isolable add-on.

## Decision

Per the pre-registered decision rule, do not start a five-attempt rescue
chain on abox01. Move to the next case in the escalation ladder
(ascis01, then amicuse01) rather than repeating the full alapuse02_v3c
investigation cycle on this case.

abox01 remains available for a future bounded rescue attempt if the
project timeline allows revisiting it later, but it is not the active
Gate C/D demonstration case for now.
