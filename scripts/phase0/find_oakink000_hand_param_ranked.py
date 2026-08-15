from pathlib import Path
import os
import pandas as pd
import pickle

root = Path(os.environ["OAKINK_DIR"]).resolve()
row = pd.read_csv("test_splits/oakink_test.csv").iloc[0]

print("===== split000 row =====")
print(row.to_string())

obj_id = str(row.get("obj_id", ""))
intent_id = str(row.get("intent_id", ""))
subj_id = str(row.get("subj_id", ""))
img_path = str(row.get("img_path", ""))

img_tokens = [x for x in img_path.replace("\\", "/").split("/") if x]
tokens = [obj_id, intent_id, subj_id]
tokens += img_tokens
tokens = [t for t in tokens if t and t.lower() != "nan"]

print("\n===== tokens used for ranking =====")
for t in tokens:
    print(t)

base = root / "extracted" / "oakink_shape_v2"
cands = list(base.rglob(f"{obj_id}/**/hand_param.pkl"))

rows = []
for p in cands:
    s = str(p)
    score = sum(1 for t in tokens if t in s)
    rows.append((score, p))

rows.sort(key=lambda x: (-x[0], str(x[1])))

print("\n===== top ranked hand_param candidates =====")
for score, p in rows[:40]:
    print(f"score={score:02d} {p}")

print("\n===== inspect top 5 pickle keys =====")
for score, p in rows[:5]:
    print("\n---", p, "score=", score)
    try:
        with open(p, "rb") as f:
            data = pickle.load(f)
        if isinstance(data, dict):
            print("keys:", sorted(data.keys()))
            for k, v in data.items():
                try:
                    shape = getattr(v, "shape", None)
                    if shape is not None:
                        print(" ", k, "shape=", shape)
                    elif isinstance(v, (str, int, float, list, tuple)):
                        print(" ", k, "=", str(v)[:120])
                except Exception:
                    pass
        else:
            print("type:", type(data))
    except Exception as e:
        print("[ERR]", e)
