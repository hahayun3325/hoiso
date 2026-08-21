from __future__ import annotations
from collections.abc import Sequence
import math
import numpy as np

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


def mask_xyxy(mask):
    binary=np.asarray(mask)>0
    if binary.ndim!=2 or not binary.any():
        raise SelectedHandMaskError("box-prompted mask must be nonempty 2D")
    ys,xs=np.nonzero(binary)
    return [float(xs.min()),float(ys.min()),float(xs.max()+1),float(ys.max()+1)]

def segment_box_prompt(sam_backend,image_rgb,selected_detector_box,*,minimum_iou=0.10):
    image=np.ascontiguousarray(np.asarray(image_rgb))
    if image.ndim!=3 or image.shape[2]!=3:
        raise SelectedHandMaskError("box-prompt image must be HxWx3")
    target=np.asarray([_box(selected_detector_box)],dtype=np.float32)
    masks,scores,_=sam_backend.predict(image,target)
    masks=np.asarray(masks)
    if masks.ndim==2: masks=masks[None,...]
    if masks.ndim!=3 or masks.shape[0]==0:
        raise SelectedHandMaskError("SAM2 box prompt returned no mask")
    score_values=np.asarray(scores,dtype=np.float64).reshape(-1)
    if score_values.size not in (0,masks.shape[0]):
        raise SelectedHandMaskError("SAM2 box scores do not match masks")
    index=int(np.argmax(score_values)) if score_values.size else 0
    mask=(masks[index]>0).astype(np.uint8)
    actual=mask_xyxy(mask); overlap=float(iou(actual,target[0]))
    if overlap<float(minimum_iou):
        raise SelectedHandMaskError(
            f"SAM2 box mask misses Q0-selected detector box: iou={overlap:.6f}")
    return mask,{'selected_proposal_index':index,
      'selected_proposal_iou':overlap,'selected_proposal_box':actual,
      'proposal_boxes':[actual],'minimum_iou':float(minimum_iou),
      'selection_method':'Q0_selected_detector_box_to_SAM2_box_prompt'}
