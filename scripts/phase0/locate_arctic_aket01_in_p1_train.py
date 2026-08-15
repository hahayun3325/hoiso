from pathlib import Path
import numpy as np

P = Path("/home/fredcui/Projects/arctic/unpack/arctic_data/data/splits/p1_train.npy")
TARGET = "s01/ketchup_grab_01/7/00147.jpg"
SEQ = "s01/ketchup_grab_01"

data = np.load(P, allow_pickle=True).item()
imgnames = data["imgnames"]
data_dict = data["data_dict"]

print("split:", P)
print("num imgnames:", len(imgnames))
print("has seq in data_dict:", SEQ in data_dict)

hits = [i for i, x in enumerate(imgnames) if TARGET in x]
print("target:", TARGET)
print("num hits:", len(hits))
print("hits:", hits[:20])

if hits:
    idx = hits[0]
    print("imgname at hit:", imgnames[idx])

print("\n===== sequence keys =====")
seq = data_dict[SEQ]
print("seq keys:", list(seq.keys()))

for k, v in seq.items():
    if hasattr(v, "shape"):
        print(k, v.shape, v.dtype)
    elif isinstance(v, dict):
        print(k, "dict keys:", list(v.keys()))
        for kk, vv in v.items():
            if hasattr(vv, "shape"):
                print(" ", kk, vv.shape, vv.dtype)
            else:
                print(" ", kk, type(vv))
    else:
        print(k, type(v))
