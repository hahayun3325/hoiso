from pathlib import Path
import csv
import cv2
import os
from ultralytics import YOLO
from estimator.hand_object_detector.hoi_detector import hand_object_detector
from foho.configs import third_party_root

root = Path("/home/fredcui/Projects/holdse/generator/assets/ho3d_v3/train")
out_csv = Path.home() / "foho_phase0/logs/phase0_13_ho3d_detector_preflight.csv"

seqs = sorted([p for p in root.iterdir() if (p / "rgb").exists()])
candidates = []

for seq in seqs:
    imgs = sorted((seq / "rgb").glob("*.jpg"))
    if not imgs:
        continue
    pick_ids = [len(imgs)//10, len(imgs)//4, len(imgs)//2, 3*len(imgs)//4, min(len(imgs)-1, 9*len(imgs)//10)]
    for idx in sorted(set(pick_ids)):
        candidates.append(imgs[idx])

wilor_ckpt = os.path.join(third_party_root(), "estimator", "wilor_ckpt", "detector.pt")
hand_yolo = YOLO(wilor_ckpt)

rows = []

for i, img_path in enumerate(candidates):
    img = cv2.imread(str(img_path))
    if img is None:
        rows.append([i, str(img_path), "READ_FAIL", "", "", ""])
        continue

    try:
        object_bbox, hand_bbox = hand_object_detector(img)
        obj_ok = object_bbox is not None
        hand_obj_ok = hand_bbox is not None
    except Exception as e:
        obj_ok = False
        hand_obj_ok = False

    try:
        det = hand_yolo(img, conf=0.1, verbose=False, iou=0.5)[0]
        wilor_n = len(det.boxes)
    except Exception:
        wilor_n = 0

    ok = obj_ok and hand_obj_ok and wilor_n > 0
    rows.append([i, str(img_path), ok, obj_ok, hand_obj_ok, wilor_n])
    print(f"[{i}] ok={ok} obj={obj_ok} handobj_hand={hand_obj_ok} wilor={wilor_n} path={img_path}")

out_csv.parent.mkdir(parents=True, exist_ok=True)
with out_csv.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["idx", "image_path", "overall_ok", "object_bbox_ok", "hand_object_detector_hand_ok", "wilor_num_boxes"])
    writer.writerows(rows)

total = len(rows)
success = sum(1 for r in rows if r[2] is True)
print(f"\nSUCCESS_RATE={success}/{total} = {success / max(total, 1):.3f}")
print("WROTE:", out_csv)
