from pathlib import Path
import os

roots = [
    Path("/home/fredcui/Projects/BIGS-main/data/arctic_data"),
    Path("/home/fredcui/datasets/hoi/arctic/raw"),
    Path("/home/fredcui/Projects/arctic/data"),
]

target_dir_names = {
    "raw_seqs",
    "processed_seqs",
    "splits",
    "splits_json",
    "meta",
    "object_vtemplates",
    "subject_vtemplates",
    "models",
    "cropped_images",
}

for root in roots:
    print("\n" + "=" * 90)
    print("ROOT:", root)
    print("exists:", root.exists())
    print("resolved:", root.resolve() if root.exists() else "NA")
    print("=" * 90)

    if not root.exists():
        continue

    print("\n===== target directories =====")
    hits = []
    for p in root.rglob("*"):
        if p.is_dir() and p.name in target_dir_names:
            hits.append(p)

    for p in hits[:200]:
        try:
            count = sum(1 for _ in p.rglob("*") if _.is_file())
        except Exception:
            count = -1
        print(f"{p}    files={count}")

    print("\n===== sample GT-like files =====")
    patterns = [
        "**/raw_seqs/**/*.npy",
        "**/processed_seqs/**/*.npy",
        "**/splits/**/*.npy",
        "**/splits_json/**/*.json",
        "**/meta/**/*.json",
        "**/meta/**/*.obj",
        "**/object_vtemplates/**/*",
    ]
    shown = 0
    for pat in patterns:
        for p in root.glob(pat):
            if p.is_file():
                print(p)
                shown += 1
                if shown >= 120:
                    break
        if shown >= 120:
            break
