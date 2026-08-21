from __future__ import annotations
from typing import Any

ALLOWED_SPATIAL={"upper_image_hand","lower_image_hand","single_hand"}

def resolve(*,spatial_instance:str,original_is_right:bool,pixels_mirrored:bool)->dict[str,Any]:
    if spatial_instance not in ALLOWED_SPATIAL:
        raise ValueError("spatial_instance")
    if type(original_is_right) is not bool:
        raise TypeError("original_is_right")
    if type(pixels_mirrored) is not bool:
        raise TypeError("pixels_mirrored")
    canonical_is_right=original_is_right ^ pixels_mirrored
    return {"schema":"tracehoi.HandednessTransport.v1",
            "decision":"handedness_transport_closed",
            "spatial_instance":spatial_instance,
            "original_is_right":original_is_right,
            "pixels_mirrored":pixels_mirrored,
            "canonical_is_right":canonical_is_right,
            "selected_hamer_side":"right" if canonical_is_right else "left"}
