from __future__ import annotations
from collections.abc import Sequence
import math

class SelectedHandMaskError(RuntimeError):
    pass

def _box(value: Sequence[float]) -> tuple[float,float,float,float]:
    row=tuple(float(item) for item in value)
    if len(row)!=4 or not all(math.isfinite(item) for item in row):
        raise SelectedHandMaskError("box must contain four finite values")
    if row[2]<=row[0] or row[3]<=row[1]:
        raise SelectedHandMaskError("box has nonpositive area")
    return row

def transform_xyxy(box, matrix):
    x1,y1,x2,y2=_box(box)
    rows=[[float(value) for value in row] for row in matrix]
    if len(rows)!=3 or any(len(row)!=3 for row in rows):
        raise SelectedHandMaskError("transform must be 3x3")
    points=[]
    for x,y in ((x1,y1),(x2,y1),(x2,y2),(x1,y2)):
        u=rows[0][0]*x+rows[0][1]*y+rows[0][2]
        v=rows[1][0]*x+rows[1][1]*y+rows[1][2]
        w=rows[2][0]*x+rows[2][1]*y+rows[2][2]
        if not math.isfinite(w) or abs(w)<1e-12:
            raise SelectedHandMaskError("invalid homogeneous transform")
        points.append((u/w,v/w))
    return [min(x for x,_ in points),min(y for _,y in points),
            max(x for x,_ in points),max(y for _,y in points)]

def iou(left,right):
    ax1,ay1,ax2,ay2=_box(left); bx1,by1,bx2,by2=_box(right)
    inter=max(0.0,min(ax2,bx2)-max(ax1,bx1))*max(0.0,min(ay2,by2)-max(ay1,by1))
    union=(ax2-ax1)*(ay2-ay1)+(bx2-bx1)*(by2-by1)-inter
    return inter/union if union>0 else 0.0

def select_mask_proposal(proposals,selected_detector_box,*,minimum_iou=0.10):
    boxes=[_box(row) for row in proposals]
    if not boxes: raise SelectedHandMaskError("no hand-mask proposal")
    target=_box(selected_detector_box); scores=[iou(row,target) for row in boxes]
    index=max(range(len(scores)),key=scores.__getitem__); score=float(scores[index])
    if score<float(minimum_iou):
        raise SelectedHandMaskError(
            f"no proposal matches Q0-selected detector box: best_iou={score:.6f}")
    return {'selected_proposal_index':index,'selected_proposal_iou':score,
            'selected_proposal_box':list(boxes[index]),
            'proposal_boxes':[list(row) for row in boxes],
            'minimum_iou':float(minimum_iou)}
