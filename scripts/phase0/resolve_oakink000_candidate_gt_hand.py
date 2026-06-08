from pathlib import Path
import os
import pandas as pd
import pickle
import json

root = Path(os.environ["OAKINK_DIR"]).resolve()
row = pd.read_csv("test_splits/oakink_test.csv").iloc[0]

obj_id = str(row["obj_id"])
intent_id = int(row["intent_id"])
subj_id = int(row["subj_id"])
img_path = str(row["img_path"])

# From previous search: exact metadata hit.
instance_id = "d846cc7ddf"

# Hypothesis from subj_id=2 and discovered s01102 folders.
subject_tag = f"s011{subj_id:02d}"

candidate = root / "extracted/oakink_shape_v2/trigger_sprayer" / obj_id / instance_id / subject_tag / "hand_param.pkl"
source = root / "extracted/oakink_shape_v2/trigger_sprayer" / obj_id / instance_id / "source.txt"
obj_mesh = root / "extracted/obj" / f"{obj_id}.obj"

report = {
    "split_row": row.to_dict(),
    "obj_id": obj_id,
    "intent_id": intent_id,
    "subj_id": subj_id,
    "img_path": img_path,
    "hypothesis": {
        "instance_id": instance_id,
        "subject_tag": subject_tag,
        "hand_param": str(candidate),
        "source_txt": str(source),
        "obj_mesh": str(obj_mesh),
    },
    "exists": {
        "hand_param": candidate.exists(),
        "source_txt": source.exists(),
        "obj_mesh": obj_mesh.exists(),
        "image": (root / "/".join(Path(img_path).parts[1:])).exists() if img_path.startswith("OakInk/") else (root / img_path).exists(),
    }
}

print("===== candidate report =====")
print(json.dumps(report, indent=2))

if source.exists():
    print("\n===== source.txt =====")
    print(source.read_text(errors="ignore"))

if candidate.exists():
    print("\n===== hand_param keys =====")
    with open(candidate, "rb") as f:
        data = pickle.load(f)
    print(type(data))
    if isinstance(data, dict):
        for k, v in data.items():
            shape = getattr(v, "shape", None)
            print(k, "shape=", shape, "type=", type(v))

out = Path.home() / "foho_phase0/inspection/oakink_000/oakink000_candidate_gt_hand_report.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2))
print("\n[OK] wrote", out)
