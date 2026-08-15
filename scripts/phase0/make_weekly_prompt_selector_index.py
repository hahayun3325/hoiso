from pathlib import Path
from PIL import Image, ImageDraw

asset_list = Path.home() / "foho_phase0/inspection/weekly_sheets/existing_visual_assets.txt"
out = Path.home() / "foho_phase0/inspection/weekly_sheets/weekly_existing_assets_contact_sheet.jpg"

paths = [Path(x.strip()) for x in asset_list.read_text().splitlines() if x.strip()]
paths = [p for p in paths if p.exists()][:24]

cards = []
for p in paths:
    im = Image.open(p).convert("RGB")
    im.thumbnail((260, 180))
    canvas = Image.new("RGB", (300, 240), "white")
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), p.name[:40], fill=(0,0,0))
    d.text((8, 220), str(p.parent).replace(str(Path.home()), "~")[-45:], fill=(80,80,80))
    canvas.paste(im, ((300-im.width)//2, 35))
    cards.append(canvas)

cols = 4
rows = max(1, (len(cards) + cols - 1)//cols)
sheet = Image.new("RGB", (300*cols, 240*rows), "white")
for i, c in enumerate(cards):
    sheet.paste(c, ((i%cols)*300, (i//cols)*240))

sheet.save(out, quality=95)
print("[OK] wrote", out)
