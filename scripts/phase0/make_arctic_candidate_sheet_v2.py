from pathlib import Path
from PIL import Image, ImageDraw
import pandas as pd

out_dir = Path.home() / "foho_phase0/inspection/official_candidates"
out_dir.mkdir(parents=True, exist_ok=True)

root = Path("/home/fredcui/Projects/arctic/data/cropped_images_structured")
split = pd.read_csv("test_splits/arctic_test.csv")

# Split-based examples.
keywords = [
    "box_grab_01",
    "ketchup_grab_01",
    "scissors_grab_01",
    "laptop_grab_01",
    "microwave_grab_01",
    "notebook_use_01",
    "phone_grab_01",
]

rows = []

def parse_split_path(img_path):
    parts = Path(img_path).parts
    if "cropped_images" not in parts:
        return None, None, None
    idx = parts.index("cropped_images")
    rel = Path(*parts[idx + 1:])
    # rel = s01/seq/view/frame.jpg
    angle = rel.parts[2] if len(rel.parts) >= 4 else "?"
    frame = Path(rel.name).stem
    return root / rel, angle, frame

for kw in keywords:
    hit = split[split["sid_seq_name"].astype(str).str.contains(kw, case=False, na=False)].head(2)
    for _, r in hit.iterrows():
        p, angle, frame = parse_split_path(r["img_path"])
        rows.append({
            "source": "split",
            "img_id": r["img_id"],
            "seq": r["sid_seq_name"],
            "angle": angle,
            "frame": frame,
            "path": str(p),
            "exists": p.exists() if p else False,
            "purpose": "rigid/thin candidate",
        })

# Manual articulated examples.
manual = [
    {
        "source": "manual",
        "img_id": "manual_laptop_use",
        "seq": "s01/laptop_use_01",
        "angle": "0",
        "frame": "00114",
        "path": root / "s01/laptop_use_01/0/00114.jpg",
        "purpose": "articulated laptop opening",
    },
    {
        "source": "manual",
        "img_id": "manual_microwave_use",
        "seq": "s01/microwave_use_01",
        "angle": "0",
        "frame": "00152",
        "path": root / "s01/microwave_use_01/0/00152.jpg",
        "purpose": "articulated microwave door",
    },
]

for m in manual:
    p = Path(m["path"])
    rows.append({
        **m,
        "path": str(p),
        "exists": p.exists(),
    })

df = pd.DataFrame(rows)
df.to_csv(out_dir / "arctic_candidate_selected_v2.csv", index=False)

thumbs = []
for _, r in df.iterrows():
    p = Path(r["path"])
    canvas = Image.new("RGB", (360, 300), "white")
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), f'id={r["img_id"]} frame={r["frame"]}', fill=(0,0,0))
    d.text((8, 28), f'angle={r["angle"]}  {r["source"]}', fill=(80,80,80))
    d.text((8, 250), str(r["seq"])[:42], fill=(0,0,0))
    d.text((8, 270), str(r["purpose"])[:44], fill=(80,80,80))

    if p.exists():
        im = Image.open(p).convert("RGB")
        im.thumbnail((320, 210))
        canvas.paste(im, ((360 - im.width)//2, 55))
    else:
        d.text((20, 130), "MISSING", fill=(180,0,0))

    thumbs.append(canvas)

cols = 3
rows_n = max(1, (len(thumbs) + cols - 1) // cols)
sheet = Image.new("RGB", (360 * cols, 300 * rows_n), "white")
for i, im in enumerate(thumbs):
    sheet.paste(im, ((i % cols) * 360, (i // cols) * 300))

out_img = out_dir / "arctic_candidate_sheet_v2_angle_articulation.jpg"
sheet.save(out_img, quality=95)

print("[OK] wrote", out_dir / "arctic_candidate_selected_v2.csv")
print("[OK] wrote", out_img)
print(df[["img_id", "seq", "angle", "frame", "exists", "purpose"]])
