from pathlib import Path
import pickle
import numpy as np

ROOT = Path.home() / "foho_phase0/inspection/oakink_000/gt_assets/oakink_image_annotation/frame90/anno"
SEQ = "A01023_0001_0002__2021-10-12-17-13-00__0__90"

def load_pkl(p):
    with open(p, "rb") as f:
        return pickle.load(f)

print("===== OakInk split000 frame90 annotation summary =====")

for view_id in range(4):
    suffix = f"{SEQ}__{view_id}.pkl"

    paths = {
        "hand_v": ROOT / "hand_v" / suffix,
        "hand_j": ROOT / "hand_j" / suffix,
        "cam_intr": ROOT / "cam_intr" / suffix,
        "obj_transf": ROOT / "obj_transf" / suffix,
        "general_info": ROOT / "general_info" / suffix,
    }

    print("")
    print("=" * 60)
    print(f"view_id={view_id}")
    print("=" * 60)

    for name, p in paths.items():
        print(f"{name}: {'OK' if p.exists() else 'MISS'} {p}")

    if all(p.exists() for p in paths.values()):
        hand_v = np.asarray(load_pkl(paths["hand_v"]))
        hand_j = np.asarray(load_pkl(paths["hand_j"]))
        K = np.asarray(load_pkl(paths["cam_intr"]))
        T_obj = np.asarray(load_pkl(paths["obj_transf"]))
        info = load_pkl(paths["general_info"])

        print("hand_v:", hand_v.shape, "z_range=", [float(hand_v[:,2].min()), float(hand_v[:,2].max())])
        print("hand_j:", hand_j.shape, "z_range=", [float(hand_j[:,2].min()), float(hand_j[:,2].max())])
        print("K:", K.tolist())
        print("obj_transf translation:", T_obj[:3, 3].tolist())
        print("general_info keys:", list(info.keys()))
        print("general_info hand keys:", list(info["hand_anno"].keys()))
        print("general_info obj_anno shape:", np.asarray(info["obj_anno"]).shape)
