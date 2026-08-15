from pathlib import Path
import numpy as np

P = Path("/home/fredcui/Projects/arctic/outputs/processed_verts/seqs/s01/ketchup_grab_01.npy")
FRAME = 147
VIEW_ID = 7

print("file:", P)
print("exists:", P.exists())

data = np.load(P, allow_pickle=True)
if data.shape == ():
    data = data.item()

print("type:", type(data))
print("keys:", list(data.keys()) if isinstance(data, dict) else "NA")

if isinstance(data, dict):
    for k, v in data.items():
        if hasattr(v, "shape"):
            print(f"{k}: shape={v.shape} dtype={v.dtype}")
            try:
                sample = v[FRAME, VIEW_ID]
                print(f"  sample frame={FRAME}, view={VIEW_ID}: shape={sample.shape}")
                if hasattr(sample, "ndim") and sample.ndim == 2:
                    print("  min:", sample.min(axis=0))
                    print("  max:", sample.max(axis=0))
            except Exception as e:
                print("  sample error:", repr(e))
        else:
            print(k, type(v))
