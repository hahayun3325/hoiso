from pathlib import Path
import os
import zipfile

root = Path(os.environ["OAKINK_DIR"]).resolve()
ann = next(iter(sorted(
    list(root.glob("image/anno_v2.1.zip")) +
    list(root.glob("image/anno_v2_1.zip")) +
    list(root.glob("zipped/image/anno_v2.1.zip")) +
    list(root.glob("zipped/image/anno_v2_1.zip"))
)), None)

if ann is None:
    raise SystemExit("[BAD] annotation zip not found")

seq = "A01023_0001_0002"
ts = "2021-10-12-17-13-00"
frame = "90"

out = Path.home() / "foho_phase0/inspection/oakink_000/gt_assets/oakink_image_annotation/frame90"
out.mkdir(parents=True, exist_ok=True)

with zipfile.ZipFile(ann) as zf:
    names = zf.namelist()

    hits = [
        n for n in names
        if seq in n
        and ts in n
        and (f"__{frame}__" in n or f"_{frame}." in n or f"color_{frame}" in n)
    ]

    print("ANN:", ann)
    print("num_hits:", len(hits))

    for n in hits:
        target = out / n
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(n) as src, open(target, "wb") as dst:
            dst.write(src.read())
        print("[OK]", n, "->", target)

print("\nOUT:", out)
