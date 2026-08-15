from pathlib import Path
from PIL import Image, ImageDraw

items = [
    (
        "Figure 1: HO3D SPAM prompt + selector diagnosis",
        Path.home() / "foho_phase0/inspection/prompt_ablation/smoke013_015_016_017_comparison_sheet.jpg",
        "Generic prompt causes shape drift; structured prompt improves object prior; final guidance can fragment object."
    ),
    (
        "Figure 2: Official OakInk split000 smoke result",
        Path.home() / "foho_phase0/inspection/oakink_000/oakink_000_visual_selector_sheet.jpg",
        "Vague prompt creates hybrid spray-bottle inpaint; selector chooses lower-fragmentation final object."
    ),
]

out = Path.home() / "foho_phase0/inspection/weekly_report_final/weekly_final_summary_panel.jpg"
out.parent.mkdir(parents=True, exist_ok=True)

cards = []
for title, path, caption in items:
    canvas = Image.new("RGB", (1500, 620), "white")
    d = ImageDraw.Draw(canvas)
    d.text((20, 15), title, fill=(0, 0, 0))
    d.text((20, 585), caption[:180], fill=(50, 50, 50))

    if path.exists():
        im = Image.open(path).convert("RGB")
        im.thumbnail((1460, 530))
        canvas.paste(im, ((1500 - im.width) // 2, 50))
    else:
        d.text((40, 280), f"MISSING: {path}", fill=(180, 0, 0))

    cards.append(canvas)

sheet = Image.new("RGB", (1500, 620 * len(cards)), "white")
for i, card in enumerate(cards):
    sheet.paste(card, (0, i * 620))

sheet.save(out, quality=95)
print("[OK] wrote", out)
