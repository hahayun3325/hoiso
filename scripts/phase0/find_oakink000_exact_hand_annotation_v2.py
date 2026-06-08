from pathlib import Path
import os
import pandas as pd
import pickle
import re

root = Path(os.environ["OAKINK_DIR"]).resolve()
row = pd.read_csv("test_splits/oakink_test.csv").iloc[0]

obj_id = str(row["obj_id"])
intent_id = int(row["intent_id"])
subj_id = int(row["subj_id"])
img_path = str(row["img_path"])

parts = img_path.replace("\\", "/").split("/")
seq = next((p for p in parts if p.startswith(obj_id + "_")), "")
timestamp = next((p for p in parts if re.match(r"\d{4}-\d{2}-\d{2}-", p)), "")
view_frame = parts[-1]
view = view_frame.replace(".png", "").rsplit("_", 1)[0]
frame = view_frame.replace(".png", "").rsplit("_", 1)[-1]

# This is a hypothesis, not guaranteed.
possible_subject_tags = [
    f"s011{subj_id:02d}",
    f"s{intent_id:02d}{subj_id:02d}",
    f"s{subj_id:05d}",
]

print("===== split000 row =====")
print(row.to_string())
print("\nseq:", seq)
print("timestamp:", timestamp)
print("view:", view)
print("frame:", frame)
print("possible_subject_tags:", possible_subject_tags)

print("\n===== exact image existence =====")
img_candidates = [
    root / img_path,
    root / "/".join(parts[1:]) if parts and parts[0] == "OakInk" else root / img_path,
]
for p in img_candidates:
    print("[OK]" if p.exists() else "[MISS]", p)

print("\n===== metadata files containing exact sequence/timestamp/image name =====")
needles = [seq, timestamp, view_frame, view]
meta_suffix = {".json", ".csv", ".txt", ".pkl", ".pickle", ".npz", ".npy"}
hits = []

for p in root.rglob("*"):
    if not p.is_file() or p.suffix.lower() not in meta_suffix:
        continue
    # avoid huge binary scans
    try:
        if p.stat().st_size > 50_000_000:
            continue
        raw = p.read_bytes()
        score = sum(1 for n in needles if n.encode() in raw)
        if score > 0:
            hits.append((score, p))
    except Exception:
        pass

hits.sort(key=lambda x: (-x[0], str(x[1])))
for score, p in hits[:80]:
    print(f"score={score:02d} {p}")

print("\n===== hand_param candidates ranked with subject-tag hypothesis =====")
base = root / "extracted" / "oakink_shape_v2"
cands = list(base.rglob(f"{obj_id}/**/hand_param.pkl"))

rows = []
for p in cands:
    s = str(p)
    score = 0
    if obj_id in s:
        score += 10
    for tag in possible_subject_tags:
        if tag in s:
            score += 5
    if seq and seq in s:
        score += 20
    if timestamp and timestamp in s:
        score += 20
    rows.append((score, p))

rows.sort(key=lambda x: (-x[0], str(x[1])))
for score, p in rows[:40]:
    print(f"score={score:02d} {p}")

print("\n===== inspect top 10 hand_param keys =====")
for score, p in rows[:10]:
    print("\n---", p, "score=", score)
    try:
        with open(p, "rb") as f:
            data = pickle.load(f)
        print("type:", type(data))
        if isinstance(data, dict):
            print("keys:", sorted(data.keys()))
            for k, v in data.items():
                shape = getattr(v, "shape", None)
                if shape is not None:
                    print(f"  {k}: shape={shape}")
                else:
                    print(f"  {k}: type={type(v)}")
    except Exception as e:
        print("[ERR]", e)
