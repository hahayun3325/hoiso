from pathlib import Path
import os

roots = [
    Path(os.environ.get("ARCTIC_DIR", "")),
    Path("/home/fredcui/datasets/hoi/arctic/raw"),
    Path("/home/fredcui/Projects/BIGS-main/data/arctic_data"),
    Path("/home/fredcui/Projects/arctic"),
]

for root in roots:
    if not root or str(root) == ".":
        continue
    print("\n" + "="*80)
    print("ROOT:", root)
    print("exists:", root.exists(), "resolve:", root.resolve() if root.exists() else "NA")
    print("="*80)

    if not root.exists():
        continue

    print("\n-- dirs depth<=4 --")
    for p in sorted(root.glob("*"))[:80]:
        print(p)

    print("\n-- metadata candidates --")
    count = 0
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in [".pkl", ".json", ".npz", ".npy", ".pt", ".yaml", ".yml"]:
            s = str(p).lower()
            if any(tok in s for tok in ["meta", "anno", "mano", "pose", "camera", "object", "ketchup", "box", "scissors", "laptop", "microwave"]):
                print(p)
                count += 1
                if count >= 80:
                    break

    print("\n-- mesh candidates --")
    count = 0
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in [".obj", ".ply", ".off", ".stl"]:
            print(p)
            count += 1
            if count >= 80:
                break
