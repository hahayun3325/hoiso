from pathlib import Path
from collections import Counter, defaultdict
import os
import zipfile
import re

root = Path(os.environ["OAKINK_DIR"]).resolve()
ann_candidates = sorted(
    list(root.glob("image/anno_v2.1.zip")) +
    list(root.glob("image/anno_v2_1.zip")) +
    list(root.glob("zipped/image/anno_v2.1.zip")) +
    list(root.glob("zipped/image/anno_v2_1.zip"))
)

if not ann_candidates:
    raise SystemExit("[BAD] annotation zip not found")

ann = ann_candidates[0]
seq = "A01023_0001_0002"
ts = "2021-10-12-17-13-00"

print("ANN:", ann)
print("SIZE_GB:", ann.stat().st_size / 1024**3)

with zipfile.ZipFile(ann) as zf:
    names = zf.namelist()

print("\n===== top-level prefix counts =====")
cnt = Counter()
cnt2 = Counter()
for n in names:
    parts = n.split("/")
    if len(parts) >= 1:
        cnt[parts[0]] += 1
    if len(parts) >= 2:
        cnt2["/".join(parts[:2])] += 1

for k, v in cnt.most_common(30):
    print(f"{k}: {v}")

print("\n===== second-level prefix counts =====")
for k, v in cnt2.most_common(80):
    print(f"{k}: {v}")

print("\n===== entries for split000 sequence/timestamp =====")
hits = [n for n in names if seq in n and ts in n]
print("num_hits:", len(hits))
for n in hits[:120]:
    print(n)

print("\n===== frame 90 candidates =====")
frame90 = [n for n in hits if "__90__" in n or "_90." in n or "color_90" in n]
print("num_frame90:", len(frame90))
for n in frame90:
    print(n)

print("\n===== categories containing split000 =====")
cat = defaultdict(int)
for n in hits:
    parts = n.split("/")
    key = "/".join(parts[:2]) if len(parts) >= 2 else parts[0]
    cat[key] += 1
for k, v in sorted(cat.items()):
    print(f"{k}: {v}")
