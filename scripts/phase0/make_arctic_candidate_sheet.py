from pathlib import Path
import pandas as pd
from PIL import Image, ImageDraw

split = pd.read_csv("test_splits/arctic_test.csv")

root = Path("/home/fredcui/Projects/arctic/data/cropped_images_structured")
out_dir = Path.home() / "foho_phase0/inspection/official_candidates"
out_dir.mkdir(parents=True, exist_ok=True)

keywords = [
    "box_grab_01",
    "ketchup_grab_01",
    "scissors_grab_01",
    "laptop_grab_01",
    "microwave_grab_01",
    "notebook_use_01",
    "phone_grab_01",
]

selected = []
for kw in keywords:
    hit = split[split["sid_seq_name"].astype(str).str.contains(kw, case=False, na=False)].head(2)
    if len(hit):
        selected.append(hit)

df = pd.concat(selected, ignore_index=True).drop_duplicates() if selected else pd.DataFrame()

def resolve_from_split_path(img_path):
    parts = Path(img_path).parts
    if "cropped_images" in parts:
        idx = parts.index("cropped_images")
        return root / Path(*parts[idx + 1:])
    return None

rows = []
thumbs = []

for _, r in df.iterrows():
    p = resolve_from_split_path(r["img_path"])
    exists = bool(p and p.exists())

    rows.append({
        "img_id": r["img_id"],
        "sid_seq_name": r["sid_seq_name"],
        "frame": r["frame"],
        "path": str(p) if p else "",
        "exists": exists,
    })

    if exists:
        im = Image.open(p).convert("RGB")
        im.thumbnail((260, 190))
        canvas = Image.new("RGB", (330, 280), "white")
        d = ImageDraw.Draw(canvas)
        d.text((8, 8), f'id={r["img_id"]} frame={r["frame"]}', fill=(0,0,0))
        d.text((8, 230), str(r["sid_seq_name"])[:42], fill=(0,0,0))
        canvas.paste(im, ((330 - im.width)//2, 35))
        thumbs.append(canvas)

out_csv = out_dir / "arctic_candidate_selected.csv"
pd.DataFrame(rows).to_csv(out_csv, index=False)

cols = 3
rows_n = max(1, (len(thumbs) + cols - 1) // cols)
sheet = Image.new("RGB", (330 * cols, 280 * rows_n), "white")
for i, im in enumerate(thumbs):
    sheet.paste(im, ((i % cols) * 330, (i // cols) * 280))

out_img = out_dir / "arctic_candidate_sheet.jpg"
sheet.save(out_img, quality=95)

print("[OK] wrote", out_csv)
print("[OK] wrote", out_img)
print(pd.DataFrame(rows))
