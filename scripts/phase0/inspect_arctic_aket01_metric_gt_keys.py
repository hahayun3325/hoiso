from pathlib import Path
import numpy as np

P = Path("/home/fredcui/Projects/arctic/outputs/processed_verts/seqs/s01/ketchup_grab_01.npy")
FRAME = 147
VIEW = 7

data = np.load(P, allow_pickle=True)
if data.shape == ():
    data = data.item()

print("file:", P)
print("top keys:", list(data.keys()))

for group_name in ["cam_coord", "world_coord", "2d", "params"]:
    group = data.get(group_name, {})
    print("\n====", group_name, "====")
    if isinstance(group, dict):
        print("keys:", list(group.keys()))
        for k, v in group.items():
            if hasattr(v, "shape"):
                print(k, v.shape, v.dtype)
                try:
                    sample = v[FRAME, VIEW]
                    print("  sample shape:", getattr(sample, "shape", None))
                except Exception:
                    pass
            else:
                print(k, type(v))
