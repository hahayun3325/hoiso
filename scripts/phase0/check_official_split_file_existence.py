from pathlib import Path
import os
import pandas as pd

dataset_roots = {
    "dexycb": Path(os.environ.get("DEX_YCB_DIR", "")),
    "arctic": Path(os.environ.get("ARCTIC_DIR", "")),
    "oakink": Path(os.environ.get("OAKINK_DIR", "")),
}

split_paths = {
    "dexycb": Path("test_splits/dexycb_test.csv"),
    "arctic": Path("test_splits/arctic_test.csv"),
    "oakink": Path("test_splits/oakink_test.csv"),
}

for name, split in split_paths.items():
    print(f"\n===== {name} =====")
    root = dataset_roots[name]
    print("root:", root)
    print("root_exists:", root.exists())

    df = pd.read_csv(split).head(10)
    for _, row in df.iterrows():
        rel = Path(row["img_path"])
        candidates = [
            root / rel,
            root.parent / rel if root.parent else root / rel,
            Path("/home/fredcui/datasets") / rel,
            Path("/home/fredcui/datasets/oakink") / rel,
        ]
        hit = next((p for p in candidates if p.exists()), None)
        print(row["img_id"], rel, "[OK]" if hit else "[MISSING]", hit if hit else "")
