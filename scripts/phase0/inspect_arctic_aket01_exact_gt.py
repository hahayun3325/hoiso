from pathlib import Path
import json
import numpy as np

GT = Path("/home/fredcui/Projects/arctic/unpack/arctic_data/data")
SUBJECT = "s01"
SEQ = "ketchup_grab_01"
OBJ = "ketchup"
VIEW_ID = 7
FRAME = 147

paths = {
    "mano": GT / "raw_seqs" / SUBJECT / f"{SEQ}.mano.npy",
    "object": GT / "raw_seqs" / SUBJECT / f"{SEQ}.object.npy",
    "egocam": GT / "raw_seqs" / SUBJECT / f"{SEQ}.egocam.dist.npy",
    "smplx": GT / "raw_seqs" / SUBJECT / f"{SEQ}.smplx.npy",
    "mesh": GT / "meta/object_vtemplates" / OBJ / "mesh.obj",
    "top": GT / "meta/object_vtemplates" / OBJ / "top.obj",
    "bottom": GT / "meta/object_vtemplates" / OBJ / "bottom.obj",
    "parts": GT / "meta/object_vtemplates" / OBJ / "parts.json",
    "params": GT / "meta/object_vtemplates" / OBJ / "object_params.json",
}

print("===== exact aket01 GT files =====")
for k, p in paths.items():
    print(f"{k:10s}", "[OK]" if p.exists() else "[MISS]", p)

print("\n===== raw object pose =====")
obj = np.load(paths["object"], allow_pickle=True)
print("object shape:", obj.shape, "dtype:", obj.dtype)
print("frame valid:", FRAME < len(obj))
if FRAME < len(obj):
    print("object pose at frame", FRAME, ":", obj[FRAME])
    print("meaning: [articulation, axis-angle rot(3), translation(3)] according to ARCTIC docs")

print("\n===== MANO file =====")
mano = np.load(paths["mano"], allow_pickle=True)
print("mano shape:", mano.shape, "dtype:", mano.dtype)
if mano.shape == ():
    mano = mano.item()
    print("mano keys:", list(mano.keys()))
    for k, v in mano.items():
        if hasattr(v, "shape"):
            print(" ", k, v.shape, v.dtype)
        else:
            print(" ", k, type(v))

print("\n===== egocam file =====")
ego = np.load(paths["egocam"], allow_pickle=True)
print("egocam shape:", ego.shape, "dtype:", ego.dtype)
if ego.shape == ():
    ego = ego.item()
    print("egocam keys:", list(ego.keys()))
    for k, v in ego.items():
        if hasattr(v, "shape"):
            print(" ", k, v.shape, v.dtype)
        else:
            print(" ", k, type(v))

print("\n===== object params =====")
with open(paths["params"], "r") as f:
    params = json.load(f)
print("object_params keys:", list(params.keys()))
