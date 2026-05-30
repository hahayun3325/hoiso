from pathlib import Path
import os
import pandas as pd

dataset_roots = {
    "dexycb": [
        Path(os.environ.get("DEX_YCB_DIR", "")),
        Path("/home/fredcui/datasets/hoi/dexycb/raw"),
        Path("/home/fredcui/datasets/dexycb"),
        Path("/home/fredcui/datasets/DexYCB"),
    ],
    "arctic": [
        Path(os.environ.get("ARCTIC_DIR", "")),
        Path("/home/fredcui/datasets/hoi/arctic/raw"),
        Path("/home/fredcui/datasets/arctic"),
        Path("/home/fredcui/Projects/arctic"),
        Path("/home/fredcui/Projects/BIGS-main/data/arctic_data"),
    ],
    "oakink": [
        Path(os.environ.get("OAKINK_DIR", "")),
        Path("/home/fredcui/datasets/hoi/oakink/raw"),
        Path("/home/fredcui/datasets/oakink"),
        Path("/home/fredcui/datasets"),
    ],
}

split_paths = {
    "dexycb": Path("test_splits/dexycb_test.csv"),
    "arctic": Path("test_splits/arctic_test.csv"),
    "oakink": Path("test_splits/oakink_test.csv"),
}


def candidate_paths(root: Path, rel: Path):
    parts = rel.parts
    out = []

    # original path
    out.append(root / rel)

    # try stripping leading components
    for i in range(1, min(len(parts), 8)):
        out.append(root / Path(*parts[i:]))

    return out


for name, split in split_paths.items():
    print(f"\n===== {name} =====")
    roots = [r for r in dataset_roots[name] if str(r) and r.exists()]
    print("existing_roots:")
    for r in roots:
        print("  ", r)

    df = pd.read_csv(split).head(10)
    ok_count = 0

    for _, row in df.iterrows():
        rel = Path(row["img_path"])
        hit = None

        for root in roots:
            for p in candidate_paths(root, rel):
                if p.exists():
                    hit = p
                    break
            if hit:
                break

        if hit:
            ok_count += 1

        print(row["img_id"], rel, "[OK]" if hit else "[MISSING]", hit if hit else "")

    print(f"SUMMARY {name}: {ok_count}/10 found")
