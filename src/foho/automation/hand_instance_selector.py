from __future__ import annotations
from collections.abc import Sequence
import math

ALLOWED_HAND_INSTANCES = {
    "upper_image_hand", "lower_image_hand", "single_hand",
    "ambiguous", "closest_to_object",
}

class HandInstanceSelectionError(RuntimeError):
    pass

def _box(box: Sequence[float]) -> tuple[float, float, float, float]:
    values = tuple(float(value) for value in box)
    if len(values) != 4 or not all(math.isfinite(value) for value in values):
        raise HandInstanceSelectionError("one hand box is not four finite values")
    x1, y1, x2, y2 = values
    if x2 <= x1 or y2 <= y1:
        raise HandInstanceSelectionError("one hand box has nonpositive area")
    return values

def _iou(left, right) -> float:
    ax1, ay1, ax2, ay2 = _box(left)
    bx1, by1, bx2, by2 = _box(right)
    width = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    height = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = width * height
    union = (ax2-ax1)*(ay2-ay1) + (bx2-bx1)*(by2-by1) - inter
    return inter / union if union > 0 else 0.0

def select_hand_index(boxes, hand_instance: str, object_box=None) -> int:
    normalized = [_box(box) for box in boxes]
    if not normalized:
        raise HandInstanceSelectionError("no detected hand box")
    if hand_instance not in ALLOWED_HAND_INSTANCES:
        raise HandInstanceSelectionError("unsupported hand_instance: " + repr(hand_instance))
    if len(normalized) == 1:
        if hand_instance == "ambiguous":
            raise HandInstanceSelectionError("ambiguous hand owner must not be guessed")
        return 0
    if hand_instance == "single_hand":
        raise HandInstanceSelectionError("single_hand contract but multiple hands detected")
    if hand_instance == "ambiguous":
        raise HandInstanceSelectionError("ambiguous hand owner must not be guessed")
    centers_y = [(box[1] + box[3]) * 0.5 for box in normalized]
    if hand_instance == "upper_image_hand":
        return min(range(len(normalized)), key=lambda index: centers_y[index])
    if hand_instance == "lower_image_hand":
        return max(range(len(normalized)), key=lambda index: centers_y[index])
    if object_box is None:
        raise HandInstanceSelectionError("closest_to_object requires object_box")
    return max(range(len(normalized)), key=lambda index: _iou(normalized[index], object_box))
