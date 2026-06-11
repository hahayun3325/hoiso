from pathlib import Path
from PIL import Image, ImageDraw
import pandas as pd

HOME = Path.home()

REPORT_DIR = HOME / "foho_phase0/inspection/arctic_phase017/final_report_assets"
OVERLAY = HOME / "foho_phase0/inspection/arctic_phase017/gt_overlay_all_cases/arctic_selected_cases_gt_2d_official_overlay_sheet.jpg"
CSV = REPORT_DIR / "arctic_selected_paper_like_metrics_surface.csv"
OUT = REPORT_DIR / "arctic_selected_paper_like_metric_overlay.jpg"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV)

avg = df.groupby("label")[["object_cd_mm", "f5", "f10", "hand_align_cd_mm"]].mean()
baseline_cd = avg.loc["baseline", "object_cd_mm"]
selector_cd = avg.loc["gpt55_selector", "object_cd_mm"]
improvement = baseline_cd - selector_cd
rel = improvement / baseline_cd * 100.0

base = Image.open(OVERLAY).convert("RGB")
base.thumbnail((1100, 1600))

W = 1700
H = max(base.height, 1200)
canvas = Image.new("RGB", (W, H), "white")
canvas.paste(base, (0, 0))
draw = ImageDraw.Draw(canvas)

x0 = base.width + 40
y = 40

draw.text((x0, y), "ARCTIC Phase 0.17 Selected-Case Metrics", fill="black")
y += 40
draw.text((x0, y), "5 manually selected ARCTIC samples", fill="black")
y += 35
draw.text((x0, y), "Evaluation: hand-aligned, surface-sampled object CD/F5/F10", fill="black")
y += 50

draw.text((x0, y), "Method averages", fill="black")
y += 35

for label in ["baseline", "gpt55_selector"]:
    row = avg.loc[label]
    draw.text((x0, y), f"{label}", fill="black")
    y += 28
    draw.text((x0 + 20, y), f"Object CD: {row['object_cd_mm']:.2f} mm", fill="black")
    y += 24
    draw.text((x0 + 20, y), f"F5: {row['f5']:.4f}", fill="black")
    y += 24
    draw.text((x0 + 20, y), f"F10: {row['f10']:.4f}", fill="black")
    y += 24
    draw.text((x0 + 20, y), f"Hand align CD: {row['hand_align_cd_mm']:.2f} mm", fill="black")
    y += 40

draw.text((x0, y), f"Mean CD improvement: {improvement:.2f} mm ({rel:.2f}%)", fill="black")
y += 50

draw.text((x0, y), "Per-case selector CD delta", fill="black")
y += 35

piv = df.pivot(index="case", columns="label", values="object_cd_mm")
for case in piv.index:
    delta = piv.loc[case, "gpt55_selector"] - piv.loc[case, "baseline"]
    mark = "better" if delta < 0 else "worse"
    draw.text((x0, y), f"{case}: {delta:+.2f} mm ({mark})", fill="black")
    y += 26

y += 30
draw.text((x0, y), "Note: GT annotations use official ARCTIC crop transform.", fill="black")
y += 25
draw.text((x0, y), "This is selected-case evaluation, not full benchmark.", fill="black")

canvas.save(OUT)
print("[OK] wrote", OUT)
