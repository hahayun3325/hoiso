from pathlib import Path
import os
import pandas as pd

root = Path(os.environ["OAKINK_DIR"]).resolve()
df = pd.read_csv("test_splits/oakink_test.csv")
row = df.iloc[0]

print("===== split000 row =====")
print(row.to_string())

img_path = str(row["img_path"])
obj_id = str(row["obj_id"])

tokens = []
for x in img_path.replace("\\", "/").split("/"):
    if x and x not in ["OakInk", "image"]:
        tokens.append(x)
tokens.append(obj_id)

print("\n===== tokens =====")
for t in tokens:
    print(t)

print("\n===== matching files =====")
all_files = list(root.rglob("*"))
for f in all_files:
    if not f.is_file():
        continue
    s = str(f)
    if any(t in s for t in tokens) and f.suffix.lower() in [".pkl", ".pickle", ".json", ".npz", ".npy", ".obj", ".ply", ".png", ".jpg"]:
        print(f)

print("\n===== hand_param candidates =====")
for f in root.rglob("hand_param.pkl"):
    s = str(f)
    if any(t in s for t in tokens):
        print(f)

print("\n===== all hand_param sample =====")
for i, f in enumerate(root.rglob("hand_param.pkl")):
    if i >= 50:
        break
    print(f)
