from __future__ import annotations
import hashlib,json,math,os
from pathlib import Path
from typing import Any
import numpy as np

class SelectedHandHaMeRError(RuntimeError): pass

def sha(path: str|Path)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _box(value)->tuple[float,float,float,float]:
    row=tuple(float(item) for item in value)
    if len(row)!=4 or not all(math.isfinite(item) for item in row):
        raise SelectedHandHaMeRError("box must contain four finite values")
    if row[2]<=row[0] or row[3]<=row[1]:
        raise SelectedHandHaMeRError("box has nonpositive area")
    return row

def iou(left,right)->float:
    ax1,ay1,ax2,ay2=_box(left); bx1,by1,bx2,by2=_box(right)
    inter=max(0.0,min(ax2,bx2)-max(ax1,bx1))*max(0.0,min(ay2,by2)-max(ay1,by1))
    union=(ax2-ax1)*(ay2-ay1)+(bx2-bx1)*(by2-by1)-inter
    return inter/union if union>0 else 0.0

def owner_from_inventory(path: str|Path)->tuple[dict[str,Any],Path,str]:
    packet=json.loads(Path(path).read_text())
    if packet.get("decision")!="foundation_stage_artifact_inventory_closed":
        raise SelectedHandHaMeRError("preprocess inventory not closed")
    rows=[row for root in packet.get("output_roots",[]) for row in root.get("files",[])
          if Path(row.get("path","")).name.endswith("_selected_hand_owner.json")]
    if len(rows)!=1: raise SelectedHandHaMeRError(f"selected owner count:{len(rows)}")
    owner_path=Path(rows[0]["path"])
    if not owner_path.is_file() or sha(owner_path)!=rows[0].get("sha256"):
        raise SelectedHandHaMeRError("selected owner inventory hash")
    owner=json.loads(owner_path.read_text())
    if owner.get("decision")!="Q0_selected_detector_to_hand_mask_closed":
        raise SelectedHandHaMeRError("selected owner decision")
    if not isinstance(owner.get("selected_hand_id"),str) or not owner["selected_hand_id"]:
        raise SelectedHandHaMeRError("selected hand id")
    if type(owner.get("canonical_is_right")) is not bool:
        raise SelectedHandHaMeRError("canonical side")
    _box(owner.get("crop_detector_box",()))
    return owner,owner_path,rows[0]["sha256"]

def selected_crop_from_inventory(path: str|Path)->Path:
    owner,_,_=owner_from_inventory(path)
    record=(owner.get("artifacts") or {}).get("crop") or {}
    crop=Path(record.get("path",""))
    if not crop.is_file() or sha(crop)!=record.get("sha256"):
        raise SelectedHandHaMeRError("selected crop hash")
    return crop

def select_candidate(inventory_path: str|Path,boxes,is_right,*,minimum_iou:float=0.10,
                     ambiguity_tolerance:float=1e-6)->dict[str,Any]:
    owner,owner_path,owner_sha=owner_from_inventory(inventory_path)
    values=np.asarray(boxes,dtype=float); sides=np.asarray(is_right).astype(bool).reshape(-1)
    if values.ndim!=2 or values.shape[1:]!=(4,) or len(values)!=len(sides) or not len(values):
        raise SelectedHandHaMeRError("candidate shapes")
    compatible=np.flatnonzero(sides==owner["canonical_is_right"])
    if not len(compatible): raise SelectedHandHaMeRError("no canonical-side HaMeR candidate")
    scores=np.asarray([iou(values[index],owner["crop_detector_box"]) for index in compatible])
    best=float(scores.max())
    if best<float(minimum_iou): raise SelectedHandHaMeRError(f"HaMeR candidate IoU:{best:.6f}")
    winners=compatible[np.flatnonzero(np.abs(scores-best)<=float(ambiguity_tolerance))]
    if len(winners)!=1: raise SelectedHandHaMeRError(f"ambiguous HaMeR candidates:{winners.tolist()}")
    index=int(winners[0])
    return {"schema":"tracehoi.SelectedHandHaMeRCandidate.v1",
      "selected_hand_owner":str(owner_path.resolve()),"selected_hand_owner_sha256":owner_sha,
      "selected_hand_id":owner["selected_hand_id"],"canonical_is_right":owner["canonical_is_right"],
      "candidate_index":index,"candidate_box":[float(x) for x in values[index]],
      "candidate_iou":best,"candidate_count":int(len(values)),"minimum_iou":float(minimum_iou),
      "selection_method":"canonical_side_then_Q0_box_IoU_unique_winner",
      "decision":"selected_hand_HaMeR_candidate_closed"}

def write_receipt(path: str|Path,payload: dict[str,Any])->None:
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix(target.suffix+".tmp")
    temporary.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    os.replace(temporary,target)
